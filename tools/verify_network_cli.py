#!/usr/bin/env python3
"""Predeclared offline real-CLI contracts; never accesses a phone or network."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = '00000000-0000000000000000'  # Inert selector; never a real device.
GUARDS = [
    ('missing-udid', ['--udid', TARGET], []),
    ('empty-udid', ['--udid', TARGET], ['--udid', '']),
    ('malformed-udid', ['--udid', TARGET], ['--udid', 'bad']),
    ('missing-host', ['--host', '192.168.1.2'], []),
    ('public-host', ['--host', '192.168.1.2'], ['--host', '8.8.8.8']),
    ('loopback-host', ['--host', '192.168.1.2'], ['--host', '127.0.0.1']),
    ('hostname', ['--host', '192.168.1.2'], ['--host', 'phone.local']),
    ('scoped-ip', ['--host', '192.168.1.2'], ['--host', 'fe80::1%eth0']),
    ('missing-port', ['--port', '12345'], []),
    ('zero-port', ['--port', '12345'], ['--port', '0']),
    ('large-port', ['--port', '12345'], ['--port', '65536']),
    ('bad-port', ['--port', '12345'], ['--port', 'bad']),
    ('missing-output', None, []),
    ('absent-output', None, []),
    ('public-output', None, []),
    ('symlink-output', None, []),
    ('checkout-output', None, []),
    ('existing-before', None, []),
    ('symlink-before', None, []),
    ('existing-after', None, ['--tap', '1', '2']),
    ('partial-tap', None, ['--tap', '1']),
    ('negative-tap', None, ['--tap', '-1', '2']),
    ('large-tap', None, ['--tap', '65536', '2']),
    ('bad-tap', None, ['--tap', 'bad', '2']),
    ('unsupported-action', None, ['--type', 'test']),
]
MODES = ['version', 'record', 'selector', 'provider-id', 'rsd-id', 'connect', 'capture', 'png', 'touch', 'release']

SITE = '''import sys, importlib.abc, importlib.util, os
from pathlib import Path
def audit(event, args):
    if event in {'socket.connect', 'socket.bind', 'socket.getaddrinfo'} or event == 'socket.__new__' and args[1] != 1:
        raise RuntimeError('offline network socket barrier')
sys.addaudithook(audit)
class Loader(importlib.abc.Loader):
    def create_module(self, spec): return None
    def exec_module(self, module):
        exec(Path(os.environ['FIXTURE_SOURCE']).read_text(), {'__name__':'offline_sdk_fixture'})
class Finder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'pymobiledevice3':
            return importlib.util.spec_from_loader(fullname, Loader(), is_package=True)
sys.meta_path.insert(0, Finder())
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='.artifacts/network-cli.json')
    args = parser.parse_args()
    results = []
    helper = ROOT / 'scripts/network_control.py'
    results.append({'name': 'helper-entrypoint', 'passed': helper.is_file()})
    scratch = Path(os.environ.get('TMPDIR', ROOT / '.artifacts/test-runs'))
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='iphone-network-cli-', dir=scratch) as tmp:
        root = Path(tmp)
        fixtures = root / 'fixtures'
        fixtures.mkdir()
        (fixtures / 'sitecustomize.py').write_text(SITE)
        for name, mode in [(n, 'guard') for n, _, _ in GUARDS] + [(n, n) for n in MODES] + [('screenshot', 'ok'), ('tap', 'ok'), ('private-ipv6', 'ok'), ('shared-private', 'ok')]:
            case = root / name
            case.mkdir(mode=0o700)
            out = case / 'output'
            out.mkdir(mode=0o700)
            events = case / 'events.jsonl'
            argv = ['--udid', TARGET, '--host', '192.168.1.2', '--port', '12345', '--output-dir', str(out)]
            if mode == 'guard':
                _, remove, add = next(g for g in GUARDS if g[0] == name)
                if remove:
                    index = argv.index(remove[0]); del argv[index:index+2]
                if name == 'missing-output': del argv[-2:]
                if name == 'absent-output': out.rmdir()
                if name == 'public-output': out.chmod(0o755)
                if name == 'symlink-output':
                    out.rmdir(); out.symlink_to(case, target_is_directory=True)
                if name == 'checkout-output': argv[-1] = str(ROOT)
                if name.startswith('existing-'):
                    (out / ('after.png' if name == 'existing-after' else 'before.png')).write_bytes(b'KEEP')
                if name == 'symlink-before': (out / 'before.png').symlink_to(case / 'untouched')
                argv += add
            if name in {'tap', 'touch', 'release'}: argv += ['--tap', '0', '65535']
            if name in {'private-ipv6', 'shared-private'}: argv[3] = 'fd00::2' if name == 'private-ipv6' else '100.64.0.2'
            env = dict(os.environ, PYTHONPATH=str(fixtures), FIXTURE_SOURCE=str(ROOT / 'tools/network_sdk_fixture.py'), FIXTURE_EVENTS=str(events), FIXTURE_MODE=mode)
            run = subprocess.run([sys.executable, str(helper), *argv], env=env, text=True, capture_output=True, timeout=15)
            entries = [json.loads(line) for line in events.read_text().splitlines()] if events.exists() else []
            passed = helper.is_file() and 'Traceback' not in run.stderr and 'SENSITIVE_SENTINEL' not in run.stdout + run.stderr and TARGET not in run.stdout + run.stderr
            if mode == 'guard':
                passed &= run.returncode == 2 and not entries
            elif mode == 'ok':
                expected = {'before.png', 'after.png'} if name == 'tap' else {'before.png'}
                passed &= run.returncode == 0 and {p.name for p in out.iterdir()} == expected
                passed &= all(p.stat().st_mode & 0o777 == 0o600 and p.read_bytes().startswith(b'\x89PNG\r\n\x1a\n') for p in out.iterdir())
                passed &= 'inspect' in run.stdout.lower() and 'verified' not in run.stdout.lower()
            else:
                passed &= run.returncode == 1
            if mode not in {'guard', 'version', 'record', 'selector'}:
                connects = [e for e in entries if e['event'] == 'connect']
                passed &= len(connects) == 1 and connects[0]['autopair'] is False and connects[0]['target'] == TARGET and connects[0]['host'] == argv[3] and connects[0]['port'] == 12345
            if mode in {'selector', 'provider-id', 'rsd-id', 'record', 'version'}:
                passed &= not any(e['event'] in {'touch', 'capture'} for e in entries)
            if name in {'tap', 'touch', 'release'}:
                passed &= [e['state'] for e in entries if e['event'] == 'touch'] == [1, 0]
                passed &= any(e['event'] == 'hid-close' for e in entries)
            if mode not in {'guard', 'version', 'record'}:
                passed &= any(e == {'event':'factory-restored', 'ok':True} for e in entries)
            if mode in {'provider-id', 'rsd-id', 'capture', 'png', 'touch', 'release', 'ok'}:
                passed &= any(e['event'] == 'provider-close' for e in entries)
            results.append({'name': name, 'passed': bool(passed), 'exit_code': run.returncode, 'events': entries, 'stdout': run.stdout[:1000], 'stderr': run.stderr[:1000]})
        # Exercise exact installed payload bytes through the real archive validator.
        bundle = ['SKILL.md','LICENSE','references/setup.md','references/commands.md','references/limits.md','templates/session-policy.yaml','references/wifi.md','scripts/network_control.py']
        for kind in ['exact', 'missing-helper', 'missing-reference', 'stale', 'extra']:
            tree = root / ('package-' + kind)
            shutil.copytree(ROOT, tree, ignore=shutil.ignore_patterns('.git','.artifacts','.venv','__pycache__'))
            archive_path = tree / 'candidate.zip'
            with zipfile.ZipFile(archive_path, 'w') as archive:
                for item in bundle:
                    if kind == 'missing-helper' and item.startswith('scripts/') or kind == 'missing-reference' and item == 'references/wifi.md': continue
                    p = ROOT / item
                    archive.writestr('iphone-control/' + item, b'STALE' if kind == 'stale' and item.startswith('scripts/') else p.read_bytes() if p.exists() else b'MISSING')
                if kind == 'extra': archive.writestr('iphone-control/private.txt', b'INERT')
            run = subprocess.run([sys.executable, str(ROOT / 'tools/validate.py'), str(tree)], text=True, capture_output=True, timeout=60)
            report = json.loads(run.stdout)
            passed = run.returncode == 0 if kind == 'exact' else run.returncode == 1 and any(e['code'] == 'archive' for e in report['errors'])
            results.append({'name':'package-'+kind, 'passed':passed, 'exit_code':run.returncode, 'report':report})
    receipt = {'scope':'Offline subprocess guards and SDK fixtures; not hardware evidence', 'helper_sha256':hashlib.sha256(helper.read_bytes()).hexdigest() if helper.exists() else None, 'cases':results, 'passed':sum(r['passed'] for r in results), 'total':len(results), 'ok':all(r['passed'] for r in results)}
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps({k:receipt[k] for k in ['scope','passed','total','ok']}))
    return 0 if receipt['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
