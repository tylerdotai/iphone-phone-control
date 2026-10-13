#!/usr/bin/env python3
"""Offline static checks for public skill documentation, not device certification.

Python standard library; Ruby/Psych parses YAML safely. Bash checks syntax only.
No snippet execution, network requests, ADB, phone access, or runtime helpers.
"""
import argparse
import binascii
import json
from pathlib import Path, PurePosixPath
import re
import struct
import subprocess
import sys
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET
import zipfile
import zlib

# Installed skill payload: exactly six files; repository artwork/tools stay out.
BUNDLE = {"SKILL.md", "LICENSE", "references/setup.md", "references/commands.md",
          "references/limits.md", "templates/session-policy.yaml"}
REQUIRED = sorted(BUNDLE | {"README.md"})
IGNORED = {".git", ".artifacts", ".venv", "__pycache__"}
PRIVATE_NAMES = {".env", "id_rsa", "id_ed25519", "adbkey", "adbkey.pub"}
YAML_RUBY = "print JSON.generate(YAML.safe_load(STDIN.read, permitted_classes: [], permitted_symbols: [], aliases: false))"


class Validator:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.errors: list[dict] = []
        self.markdown: dict[Path, str] = {}
        self.checked = 0

    def error(self, code: str, path: Path, message: str) -> None:
        try:
            name = str(path.relative_to(self.root))
        except ValueError:
            name = "outside-repository"
        self.errors.append({"code": code, "path": name, "message": message})

    def yaml(self, text: str, path: Path):
        run = subprocess.run(["ruby", "-rjson", "-ryaml", "-e", YAML_RUBY], input=text, text=True, capture_output=True, timeout=15)
        if run.returncode:
            self.error("yaml", path, "Ruby/Psych rejected YAML (unsafe tags/aliases are disallowed)")
            return None
        return json.loads(run.stdout)

    def privacy(self, text: str, path: Path) -> None:
        patterns = [r"/home/[A-Za-z0-9_.-]+/", r"/Users/[A-Za-z0-9_.-]+/",
                    r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----",
                    r"gh[pousr]_[A-Za-z0-9]{30,}", r"github_pat_[A-Za-z0-9_]{40,}",
                    r"AKIA[A-Z0-9]{16}", r"sk-[A-Za-z0-9_-]{32,}"]
        if any(re.search(pattern, text) for pattern in patterns):
            self.error("privacy", path, "Private path or credential-shaped value; inspect privately (value not echoed)")
        for value in re.findall(r'\bSERIAL\s*=\s*[\"\x27]([^\"\x27]+)[\"\x27]', text):
            if not any(symbol in value for symbol in ("$", "<", ">")):
                self.error("privacy", path, "Literal device serial assignment; use an explicit placeholder")
        if re.search(r"\badb\s+-s\s+(?![\"\x27]?\$|[\"\x27]?<)[A-Za-z0-9]{8,}", text):
            self.error("privacy", path, "Literal device selector; use SERIAL")
        if re.search(r"https://github\.com/tylerdotai/iphone-phone-(?!control(?:[/#\s.)\"\x27]|$))[A-Za-z0-9_-]+", text):
            self.error("public-url", path, "Stale public repository URL")

    def png(self, data: bytes, path: Path) -> None:
        try:
            if not data.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError("signature")
            offset, types, compressed = 8, [], bytearray()
            width = height = 0
            while offset < len(data):
                size = struct.unpack_from(">I", data, offset)[0]
                kind = data[offset + 4:offset + 8]
                end = offset + size + 12
                if end > len(data):
                    raise ValueError("truncated chunk")
                body = data[offset + 8:offset + 8 + size]
                crc = struct.unpack_from(">I", data, offset + 8 + size)[0]
                if binascii.crc32(kind + body) & 0xffffffff != crc:
                    raise ValueError("CRC")
                if kind == b"IHDR":
                    width, height, depth, color, method, filtering, interlace = struct.unpack(">IIBBBBB", body)
                    if not (0 < width <= 16000 and 0 < height <= 16000 and depth in {1, 2, 4, 8, 16} and color in {0, 2, 3, 4, 6} and method == filtering == 0 and interlace in {0, 1}):
                        raise ValueError("IHDR")
                if kind in {b"tEXt", b"zTXt", b"iTXt"}:
                    metadata = body
                    if kind == b"zTXt":
                        keyword, payload = body.split(b"\x00", 1)
                        if not payload or payload[0] != 0:
                            raise ValueError("text compression method")
                        metadata = keyword + b"\x00" + self.inflate_metadata(payload[1:])
                    elif kind == b"iTXt":
                        keyword, payload = body.split(b"\x00", 1)
                        if len(payload) < 2 or payload[0] not in {0, 1} or payload[1] != 0:
                            raise ValueError("international text header")
                        language, translated, content = payload[2:].split(b"\x00", 2)
                        if payload[0] == 1:
                            content = self.inflate_metadata(content)
                        metadata = b"\x00".join((keyword, language, translated, content))
                    self.privacy(metadata.decode("utf-8", errors="replace"), path)
                if kind == b"eXIf":
                    raise ValueError("unreviewed EXIF metadata")
                if kind == b"IDAT":
                    compressed.extend(body)
                types.append(kind)
                offset = end
            if not types or types[0] != b"IHDR" or types[-1] != b"IEND" or not compressed or not width or not height:
                raise ValueError("required chunks")
            decoder = zlib.decompressobj()
            pixels = decoder.decompress(bytes(compressed), 64 * 1024 * 1024)
            if not pixels or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
                raise ValueError("invalid/oversized compressed image")
        except (ValueError, struct.error, zlib.error):
            self.error("png", path, "Invalid PNG header, chunks, CRC, or compressed image")

    @staticmethod
    def inflate_metadata(data: bytes) -> bytes:
        decoder = zlib.decompressobj()
        result = decoder.decompress(data, 1_000_000)
        if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
            raise ValueError("invalid/oversized compressed metadata")
        return result

    def svg(self, text: str, path: Path) -> None:
        try:
            if re.search(r"<!DOCTYPE|<!ENTITY", text, re.I):
                raise ValueError("entities")
            # Reject DTD/entity declarations before stdlib parsing; no network or
            # external entity resolution. Input also has the document size bound.
            root = ET.fromstring(text)
            if root.tag.split("}")[-1] != "svg":
                raise ValueError("root")
            if not (root.get("aria-label") or root.get("aria-labelledby") or any(element.tag.split("}")[-1] == "title" and element.text for element in root.iter())):
                raise ValueError("accessible title")
            for element in root.iter():
                if element.tag.split("}")[-1].lower() in {"script", "foreignobject"}:
                    raise ValueError("active content")
                for key, value in element.attrib.items():
                    key = key.split("}")[-1].lower()
                    if key.startswith("on") or (key in {"href", "src"} and value and not value.startswith("#")):
                        raise ValueError("external or active reference")
                    if re.search(r"url\(\s*[\"\x27]?(?!#)[^)]|@import", value, re.I):
                        raise ValueError("external paint/style reference")
                if re.search(r"url\(\s*[\"\x27]?(?!#)[^)]|@import", element.text or "", re.I):
                    raise ValueError("external stylesheet reference")
                if re.search(r"url\(\s*[\"\x27]?(?!#)[^)]", element.get("style", ""), re.I):
                    raise ValueError("external style reference")
        except (ET.ParseError, ValueError):
            self.error("svg", path, "Malformed, inaccessible, active, or externally referencing SVG")

    def archive(self, path: Path) -> None:
        try:
            with zipfile.ZipFile(path) as archive:
                seen = set()
                normalized = set()
                for entry in archive.infolist():
                    parts = PurePosixPath(entry.filename).parts
                    relative = "/".join(parts[1:]) if parts and parts[0] == "iphone-control" else entry.filename
                    if (entry.filename.startswith("/") or ".." in parts or "\\" in entry.filename
                            or (entry.external_attr >> 16) & 0o170000 == 0o120000
                            or entry.filename in seen or entry.file_size > 2_000_000):
                        raise ValueError("unsafe archive entry")
                    seen.add(entry.filename)
                    if entry.is_dir():
                        if relative.rstrip("/") not in {"", "iphone-control", "references", "templates"}:
                            raise ValueError("unexpected directory")
                        continue
                    if relative not in BUNDLE or relative in normalized:
                        raise ValueError("unexpected/private file")
                    normalized.add(relative)
                    data = archive.read(entry)
                    expected = self.root / relative
                    if not expected.is_file() or data != expected.read_bytes():
                        raise ValueError("stale bundle bytes")
                if archive.testzip():
                    raise ValueError("CRC")
                files = {("/".join(PurePosixPath(name).parts[1:]) if name.startswith("iphone-control/") else name) for name in seen if not name.endswith("/")}
                if files != BUNDLE:
                    raise ValueError("incomplete bundle")
        except (ValueError, OSError, zipfile.BadZipFile, RuntimeError):
            self.error("archive", path, "Archive must contain the exact current public skill files, safe paths, and valid CRC")

    def fences(self, text: str, path: Path) -> str:
        prose, body, delimiter, language = [], [], "", ""
        for line in text.splitlines():
            opening = re.match(r"^\s*(`{3,}|~{3,})(.*)$", line)
            if not delimiter and opening:
                delimiter, language = opening.group(1), opening.group(2).strip().lower()
                body = []
            elif delimiter and re.match(r"^\s*" + re.escape(delimiter[0]) + "{" + str(len(delimiter)) + r",}\s*$", line):
                code = "\n".join(body) + "\n"
                if language in {"bash", "sh", "shell"}:
                    run = subprocess.run(["bash", "-n"], input=code, capture_output=True, text=True, timeout=10)
                    if run.returncode:
                        self.error("bash", path, "Invalid shell fence syntax (bash -n; never executed)")
                elif language in {"python", "py", "python3"}:
                    try:
                        compile(code, str(path.name), "exec")
                    except SyntaxError:
                        self.error("python", path, "Invalid Python fence syntax (compile only)")
                delimiter = ""
            elif delimiter:
                body.append(line)
            else:
                prose.append(line)
        if delimiter:
            self.error("fence", path, "Unclosed code fence")
        return "\n".join(prose)

    @staticmethod
    def anchors(text: str) -> set[str]:
        result = set(re.findall(r'\b(?:id|name)=[\"\x27]([^\"\x27]+)[\"\x27]', text))
        counts: dict[str, int] = {}
        for heading in re.findall(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", text, re.M):
            heading = re.sub(r"<[^>]*>", "", heading)
            heading = re.sub(r"!?\[([^]]+)\]\([^)]*\)", r"\1", heading)
            slug = re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
            number = counts.get(slug, 0)
            result.add(slug + (f"-{number}" if number else ""))
            counts[slug] = number + 1
        return result

    def link(self, target: str, path: Path) -> None:
        target = target.strip().strip("<>")
        parsed = urlsplit(target)
        if parsed.scheme in {"https", "http", "mailto"}:
            return  # No CI network crawling; parent verifies public readback.
        if parsed.scheme or parsed.netloc:
            self.error("link", path, "Unsupported link scheme")
            return
        file = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
        if not file.is_relative_to(self.root) or not file.exists() or file.is_symlink():
            self.error("link", path, "Missing/escaping local target")
            return
        if parsed.fragment and file.suffix.lower() == ".md":
            text = self.markdown.get(file, "")
            if unquote(parsed.fragment) not in self.anchors(text):
                self.error("anchor", path, "Missing Markdown/HTML anchor")

    def run(self) -> dict:
        for name in REQUIRED:
            if not (self.root / name).is_file() or not (self.root / name).read_bytes().strip():
                self.error("required", self.root / name, "Missing or empty required public documentation file")
        for path in sorted(self.root.rglob("*")):
            relative = path.relative_to(self.root)
            if any(part in IGNORED for part in relative.parts):
                continue
            if path.is_symlink():
                self.error("tree", path, "Symlinks are not allowed in the public tree")
                continue
            if path.is_dir():
                continue
            self.checked += 1
            if path.name in PRIVATE_NAMES or path.suffix.lower() in {".log", ".apk", ".pem", ".key", ".mp4"}:
                self.error("tree", path, "Private/runtime evidence filename is not allowed")
            if path.stat().st_size > 10_000_000:
                self.error("tree", path, "File exceeds documentation size bound")
                continue
            if path.suffix.lower() == ".zip":
                self.archive(path)
                continue
            data = path.read_bytes()
            if path.suffix.lower() == ".png":
                self.png(data, path)
                continue
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                self.error("tree", path, "Unexpected binary file (only checked PNG/ZIP supported)")
                continue
            self.privacy(text, path)
            if path.suffix.lower() == ".svg":
                self.svg(text, path)
            if path.suffix.lower() in {".yaml", ".yml"}:
                value = self.yaml(text, path)
                if relative.as_posix() == "templates/session-policy.yaml":
                    session = value.get("session", {}) if isinstance(value, dict) else {}
                    if not isinstance(value, dict) or value.get("enforced") is not False or not isinstance(session, dict) or any(session.get(key) is not None for key in ("exact_udid", "approved_app", "private_location", "private_artifact_location")):
                        self.error("policy", path, "Policy must be unenforced and contain no live session values")
            if path.suffix.lower() == ".md":
                self.markdown[path] = self.fences(text, path)
            if path.suffix.lower() == ".py":
                try:
                    compile(text, str(relative), "exec")
                except SyntaxError:
                    self.error("python", path, "Invalid repository Python syntax")
        skill = self.root / "SKILL.md"
        if skill in self.markdown:
            match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", skill.read_text(), re.S)
            if not match:
                self.error("skill", skill, "Missing YAML frontmatter")
            else:
                meta = self.yaml(match.group(1), skill)
                if meta is not None:
                    if not isinstance(meta, dict):
                        self.error("skill", skill, "Frontmatter must be a mapping")
                    else:
                        name, description, metadata = meta.get("name"), meta.get("description"), meta.get("metadata")
                        if not isinstance(name, str) or name != "iphone-control" or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
                            self.error("skill", skill, "Skill name must match iphone-control")
                        if not isinstance(description, str) or not 1 <= len(description) <= 60 or not description.startswith("Use when "):
                            self.error("skill", skill, "Description must start Use when and be 1–60 characters")
                        if meta.get("license") != "MIT" or not isinstance(meta.get("compatibility"), str) or not isinstance(metadata, dict) or not isinstance(metadata.get("version"), str) or not metadata.get("version") or any(not isinstance(key, str) or not isinstance(value, str) for key, value in metadata.items()):
                            self.error("skill", skill, "Require MIT, compatibility string, and string-valued metadata")
        for path, text in self.markdown.items():
            definitions = {name.strip().lower(): target for name, target in re.findall(r"^\s{0,3}\[([^]]+)\]:\s*(\S+)", text, re.M)}
            for target in definitions.values():
                self.link(target, path)
            without_definitions = re.sub(r"^\s{0,3}\[[^]]+\]:.*$", "", text, flags=re.M)
            for label, target in re.findall(r"!?\[([^]\n]*)\]\(\s*(<[^>]+>|[^\s)]+)(?:\s+[\"\x27][^\n]*?[\"\x27])?\s*\)", without_definitions):
                self.link(target, path)
                if not label.strip():
                    self.error("link", path, "Image/link label must not be empty")
            for label, reference in re.findall(r"!?\[([^]\n]+)\]\[([^]\n]*)\]", without_definitions):
                if (reference or label).lower() not in definitions:
                    self.error("reference", path, "Undefined Markdown reference")
            for target in re.findall(r'\b(?:href|src)=[\"\x27]([^\"\x27]+)[\"\x27]', without_definitions):
                self.link(target, path)
            for image in re.findall(r"<img\b[^>]*>", without_definitions, re.I):
                if not re.search(r'\balt=[\"\x27][^\"\x27]+[\"\x27]', image):
                    self.error("link", path, "HTML image needs nonempty alt text")
        readme = self.root / "README.md"
        if readme in self.markdown:
            text = self.markdown[readme]
            headings = " ".join(re.findall(r"^\s*#{1,6}\s+(.+)$", text, re.M)).lower()
            for section in ("about", "built with", "getting started", "prerequisites", "installation", "usage", "roadmap", "contributing", "license", "contact", "acknowledgments"):
                if section not in headings:
                    self.error("readme", readme, "Missing required README section: " + section)
            if not re.search(r"!\[[^]]+\]\(|<img\b|!\[[^]]+\]\[", text):
                self.error("readme", readme, "README must include an image")
        return {"ok": not self.errors, "scope": "Static documentation/package checks only; no phone access or policy enforcement verified", "files_checked": self.checked, "errors": self.errors}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    validator = Validator(args.path)
    try:
        report = validator.run()
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        validator.error("environment", validator.root, "Validation could not complete: " + type(error).__name__)
        report = {"ok": False, "scope": "Static documentation only", "errors": validator.errors}
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
