#!/usr/bin/env python3
"""Offline Windows OS-guard fixture and static support-scope oracle."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SHIM = '''import asyncio, ssl, runpy, sys, pathlib, os, argparse, importlib.metadata, ipaddress, json, logging, re
helper, out = sys.argv[1:3]
sys.argv = [helper] + sys.argv[3:]
def audit(event, args):
    if event.startswith('socket.') or event == 'import' and args[0].startswith('pymobiledevice3'):
        raise RuntimeError('offline boundary crossed')
    if event == 'open' and str(args[0]).startswith(out):
        raise RuntimeError('output reservation crossed')
sys.addaudithook(audit)
sys.platform = 'win32'
runpy.run_path(helper, run_name='__main__')
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='.artifacts/windows-scope.json')
    args = parser.parse_args()
    cases = []
    helper = ROOT / 'scripts/network_control.py'
    with tempfile.TemporaryDirectory(prefix='iphone-windows-scope-', dir=os.environ['TMPDIR']) as tmp:
        out = Path(tmp) / 'output'
        out.mkdir(mode=0o700)
        base = ['--udid', '00000000-0000000000000000', '--host', '192.168.1.2', '--port', '12345', '--output-dir', str(out)]
        for name, argv in [('screenshot', base), ('tap', base + ['--tap', '1', '2']), ('help', ['--help'])]:
            run = subprocess.run([sys.executable, '-c', SHIM, str(helper), str(out), *argv], capture_output=True, text=True, timeout=15)
            passed = run.returncode == 2 and run.stdout == '' and run.stderr == 'Native Windows network helper unsupported; use Linux or POSIX macOS. No connection attempted.\n' and not list(out.iterdir())
            cases.append(dict(name='mock-win32-'+name, passed=passed, exit_code=run.returncode, stdout=run.stdout, stderr=run.stderr))
    docs = {p: (ROOT / p).read_text() for p in ['README.md', 'SKILL.md', 'references/wifi.md', 'references/limits.md']}
    for p, text in docs.items():
        cases.append(dict(name='scope-'+p, passed='Native Windows network helper unsupported' in text and 'POSIX macOS' in text))
    wifi = docs['references/wifi.md']
    cases.append(dict(name='no-windows-helper-invocations', passed='& $IphonePython $HELPER' not in wifi and 'Native PowerShell invocation uses `--tap' not in wifi))
    cases.append(dict(name='posix-file-mode-scope', passed='POSIX mode 0600' in wifi and 'POSIX mode 0600' in docs['README.md']))
    cases.append(dict(name='same-sdk-credential-environment', passed=all(s in wifi for s in ['same SDK user-data home', 'XDG_DATA_HOME', 'missing record', 'unrelated credential directories'])))
    receipt = dict(scope='Linux subprocess with mocked win32 guard; not native Windows or hardware execution; static docs oracle', helper_sha256=hashlib.sha256(helper.read_bytes()).hexdigest(), cases=cases, passed=sum(c['passed'] for c in cases), total=len(cases), ok=all(c['passed'] for c in cases))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps({k: receipt[k] for k in ['scope', 'passed', 'total', 'ok']}))
    return 0 if receipt['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
