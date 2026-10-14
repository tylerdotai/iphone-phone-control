#!/usr/bin/env python3
"""Test-first CLI contract: real repository plus bounded filesystem mutants.

Known failures are named in CASES below before validator implementation. No
phone, ADB, network, mocks, or imported validator internals are used. Captures
include each CLI exit status and JSON result. A missing/incomplete parent README
is a baseline failure, never silently replaced with a passing synthetic repo.
"""
import argparse
import binascii
import struct
import zlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

CASES = [
    ("local-environment-ignored", "allowed", "write", ".venv/LOCAL_ONLY.json", '{"private_path":"/home/' + 'private-person/local-environment"}\n'),
    ("missing-skill", "required", "remove", "SKILL.md", ""),
    ("missing-reference", "required", "remove", "references/setup.md", ""),
    ("malformed-yaml", "yaml", "write", "templates/session-policy.yaml", "broken: [\n"),
    ("bad-name", "skill", "replace", "SKILL.md", "name: iphone-control|name: Bad_Name"),
    ("long-description", "skill", "replace", "SKILL.md", 'description: "Use when observing or controlling a trusted iPhone."|description: "' + "x" * 61 + '"'),
    ("numeric-metadata", "skill", "replace", "SKILL.md", 'version: "1.1.0"|version: 1'),
    ("live-policy-udid", "policy", "replace", "templates/session-policy.yaml", "exact_udid: null|exact_udid: INERT_DEVICE_IDENTIFIER"),
    ("enforced-policy", "policy", "replace", "templates/session-policy.yaml", "enforced: false|enforced: true"),
    ("missing-image", "link", "append", "README.md", "\n![Missing](assets/not-present.png)\n"),
    ("missing-local-link", "link", "append", "README.md", "\n[Missing](references/not-present.md)\n"),
    ("missing-anchor", "anchor", "append", "README.md", "\n[Missing](SKILL.md#not-present-anchor)\n"),
    ("undefined-reference", "reference", "append", "README.md", "\n[Missing][undefined-e2e-ref]\n"),
    ("bad-bash", "bash", "append", "README.md", "\n```bash\nif then\n```\n"),
    ("bad-python", "python", "append", "README.md", "\n```python\ndef broken(\n```\n"),
    ("unclosed-fence", "fence", "append", "README.md", "\n```bash\ntrue\n"),
    ("bad-svg", "svg", "write", "assets/e2e.svg", "<svg>"),
    ("script-svg", "svg", "write", "assets/e2e.svg", '<svg xmlns="http://www.w3.org/2000/svg"><title>Test</title><script/></svg>'),
    ("external-svg", "svg", "write", "assets/e2e.svg", '<svg xmlns="http://www.w3.org/2000/svg"><title>Test</title><image href="https://example.com/image.png"/></svg>'),
    ("bad-png", "png", "write", "assets/e2e.png", "not a PNG"),
    ("private-png-metadata", "privacy", "png", "assets/e2e.png", "/home/" + "private-person/evidence"),
    ("external-svg-paint", "svg", "write", "assets/e2e.svg", '<svg xmlns="http://www.w3.org/2000/svg"><title>Test</title><rect fill="url(https://example.com/paint.svg#x)"/></svg>'),
    ("private-path", "privacy", "append", "README.md", "\n/home/" + "private-person/phone-evidence\n"),
    ("live-serial", "privacy", "append", "README.md", '\nSERIAL="' + "E2E_INERT_SERIAL_123" + '"\n'),
    ("credential-shaped", "privacy", "append", "README.md", "\n" + "gh" + "p_" + "INERT" * 8 + "\n"),
    ("private-file", "tree", "write", ".env", "INERT=1\n"),
    ("symlink", "tree", "symlink", "assets/e2e-link", "SKILL.md"),
    ("private-zip", "archive", "zip", "assets/e2e.zip", ".env"),
    ("traversal-zip", "archive", "zip", "assets/e2e.zip", "../escape.txt"),
    ("malformed-workflow", "yaml", "write", ".github/workflows/validate.yml", "jobs: [\n"),
    ("stale-repo-url", "public-url", "append", "README.md", "\nhttps://github.com/tylerdotai/iphone-phone-" + "skill\n"),
    ("missing-readme-sections", "readme", "write", "README.md", "# Incomplete\n"),
]


def invoke(validator: Path, root: Path) -> dict:
    run = subprocess.run([sys.executable, str(validator), str(root)], capture_output=True, text=True, timeout=90)
    try:
        report = json.loads(run.stdout)
    except json.JSONDecodeError:
        report = None
    return {"exit_code": run.returncode, "report": report,
            "stderr": run.stderr[:2000], "non_json_stdout": run.stdout[:2000] if report is None else ""}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=".artifacts/e2e.json")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    validator = root / "tools/validate.py"
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    results = []
    if not validator.is_file():
        results.append({"name": "validator-entrypoint", "passed": False, "reason": "missing-validator", **invoke(validator, root)})
    else:
        baseline = invoke(validator, root)
        results.append({"name": "actual-repository", "passed": baseline["exit_code"] == 0 and isinstance(baseline["report"], dict) and baseline["report"].get("ok") is True, **baseline})
        scratch = Path(os.environ.get("TMPDIR", str(root / ".artifacts/test-runs")))
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="android-docs-e2e-", dir=scratch) as directory:
            for name, code, action, relative, value in CASES:
                tree = Path(directory) / name
                shutil.copytree(root, tree, symlinks=True, ignore=shutil.ignore_patterns(".git", ".artifacts", ".venv", "__pycache__"))
                target = tree / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                if action == "remove":
                    target.unlink(missing_ok=True)
                elif action == "replace":
                    old, new = value.split("|", 1)
                    text = target.read_text()
                    if old not in text:
                        raise RuntimeError(f"Mutation precondition absent: {name}")
                    target.write_text(text.replace(old, new, 1))
                elif action == "append":
                    with target.open("a") as stream:
                        stream.write(value)
                elif action == "write":
                    target.write_text(value)
                elif action == "png":
                    # Inert 1x1 fixture, not a product/device screenshot.
                    def chunk(kind: bytes, body: bytes) -> bytes:
                        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", binascii.crc32(kind + body) & 0xffffffff)
                    target.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)) + chunk(b"tEXt", b"Comment\x00" + value.encode()) + chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00\x00")) + chunk(b"IEND", b""))
                elif action == "symlink":
                    target.symlink_to(tree / value)
                elif action == "zip":
                    with zipfile.ZipFile(target, "w") as archive:
                        archive.writestr(value, "INERT")
                result = invoke(validator, tree)
                report = result["report"]
                codes = {item.get("code") for item in report.get("errors", [])} if isinstance(report, dict) else set()
                passed = (result["exit_code"] == 0 and isinstance(report, dict) and report.get("ok") is True) if code == "allowed" else (result["exit_code"] == 1 and code in codes)
                results.append({"name": name, "expected_code": code, "passed": passed, **result})
    receipt = {"scope": "Static documentation/package validation only; no device access verified", "cases": results, "passed": sum(item["passed"] for item in results), "total": len(results), "ok": all(item["passed"] for item in results)}
    output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"ok": receipt["ok"], "passed": receipt["passed"], "total": receipt["total"], "artifact": str(output)}))
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())