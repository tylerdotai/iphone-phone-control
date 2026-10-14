# Windows network-helper repair contract (test-first)

Native Windows is unsupported by this helper, not merely untested: POSIX mode
checks cannot certify NTFS ACL privacy. Do not relax them or add an ACL workaround.
Linux hardware evidence and upstream macOS/Windows USB guidance stay separate.

Known failures, enumerated before repair:
- Windows reaches SDK import, connection, or output reservations before refusing.
- Windows screenshot, tap, or help emits a traceback, selectors, or ambiguous
  unsupported-version/privacy error instead of a fixed unsupported-host refusal.
- Root README/SKILL compatibility falsely extends network support to Windows.
- Wi-Fi instructions retain Windows helper invocations or unqualified mode 0600.
- SDK user-data-home changes after trusted USB bootstrap hide the existing record;
  docs must require the same SDK user-data home/environment (including
  XDG_DATA_HOME when set), stop on missing records, and forbid credential copying
  or searching unrelated credential directories.

The offline CLI test runs the real main entrypoint in Linux subprocesses with
only sys.platform mocked to win32 after preloading stdlib dependencies. This is
an OS-guard fixture, NOT native Windows execution. An audit hook blocks SDK
imports, sockets, and output file creation. Existing 33 and 45 checks remain.
Docs checks are a static scope oracle, not hardware certification.

Regenerate: `python3 tools/verify_windows_scope.py --output .artifacts/windows-scope.json`.
Preserve RED separately as `.artifacts/windows-scope-red.json`.
