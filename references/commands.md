# Exact-device command reference

## Select before connecting

Discovery and `--help` are the only unbound CLI examples here: they list candidates
or inspect syntax, not an authorized target for actions. Discovery output is
private. Read it locally; match the full UDID to the human-confirmed phone.

Bash (Linux/macOS, activated environment):

```bash
python -m pymobiledevice3 usbmux list
python -m pymobiledevice3 developer core-device universal-hid-service type --help
```

Native Windows PowerShell (from the approved task environment directory):

```powershell
& .\.venv\Scripts\python.exe -m pymobiledevice3 usbmux list
& .\.venv\Scripts\python.exe -m pymobiledevice3 developer core-device universal-hid-service type --help
```

Set `PYMOBILEDEVICE3_UDID` to the **exact** selected identifier in a dedicated
shell, not a profile. Never leave it empty. Do not infer target from list order.
Remove inherited `PYMOBILEDEVICE3_RECONNECT_ANY`, `PYMOBILEDEVICE3_TUNNEL`,
`PYMOBILEDEVICE3_NATIVE`, `PYMOBILEDEVICE3_USERSPACE`, and
`PYMOBILEDEVICE3_FORCE_TUNNEL` in that shell. Inspect `PYMOBILEDEVICE3_USBMUX` and
`USBMUXD_SOCKET_ADDRESS`; stop if they redirect to an unapproved host/service.
Use only explicit `--userspace` for the examples below; no `--rsd`, `--tunnel`,
`--native`, or reconnect options. Exit the dedicated shell afterward rather than
modifying persistent environment settings.

`PYMOBILEDEVICE3_UDID` is documented as the command device default. In upstream
`cli_common.py`, `_cli_udid()` reads this environment variable when no argv UDID
is present; `make_rsd_dependency()` supplies it to the userspace tunnel resolver.
Some CoreDevice help omits `--udid`; do not append an unsupported option. Before
use, inspect that dependency path in the **installed** version's source and
confirm it retains this binding. If absent/ambiguous, stop. Ordinary commands
that expose `--udid` may additionally set it to the same exact value; conflicting
CLI options override environment defaults and are forbidden here.

- [Environment variable documentation](https://doronz88.github.io/pymobiledevice3/guides/environment-variables/)
- [Upstream selector source](https://github.com/doronz88/pymobiledevice3/blob/master/pymobiledevice3/cli/cli_common.py)
- [Upstream command definitions](https://github.com/doronz88/pymobiledevice3/blob/master/pymobiledevice3/cli/developer/core_device.py)

Recheck discovery and binding after reconnect; never retarget automatically.

## One action per observation

The examples assume that exact binding and all approval gates already hold.
Do not paste the whole block: choose **one** action, then capture and inspect a
new screenshot. `screen.png` is a task-private output; choose a fresh filename
for each observation and avoid overwriting existing files.

Bash: each invocation independently rejects a missing/empty binding.

```bash
PYMOBILEDEVICE3_UDID="${PYMOBILEDEVICE3_UDID:?Bind exact confirmed UDID}" python -m pymobiledevice3 mounter auto-mount --userspace
PYMOBILEDEVICE3_UDID="${PYMOBILEDEVICE3_UDID:?Bind exact confirmed UDID}" python -m pymobiledevice3 developer core-device screen-capture screenshot screen.png --userspace
PYMOBILEDEVICE3_UDID="${PYMOBILEDEVICE3_UDID:?Bind exact confirmed UDID}" python -m pymobiledevice3 developer core-device universal-hid-service tap --userspace -- 32768 32768
PYMOBILEDEVICE3_UDID="${PYMOBILEDEVICE3_UDID:?Bind exact confirmed UDID}" python -m pymobiledevice3 developer core-device universal-hid-service type --userspace --char-delay 0.06 --inter-delay 0.04 -- 'Blue'
PYMOBILEDEVICE3_UDID="${PYMOBILEDEVICE3_UDID:?Bind exact confirmed UDID}" python -m pymobiledevice3 developer core-device universal-hid-service drag --userspace --duration 0.4 --steps 20 -- 32768 50000 32768 20000
PYMOBILEDEVICE3_UDID="${PYMOBILEDEVICE3_UDID:?Bind exact confirmed UDID}" python -m pymobiledevice3 developer core-device hid button home press --userspace
```

PowerShell: every invocation has a nonempty-binding guard. A new shell starts
unbound; replace neither the guard nor the identifier with default-first logic.

```powershell
if ([string]::IsNullOrWhiteSpace($env:PYMOBILEDEVICE3_UDID)) { throw 'Bind exact confirmed UDID' }; & .\.venv\Scripts\python.exe -m pymobiledevice3 mounter auto-mount --userspace
if ([string]::IsNullOrWhiteSpace($env:PYMOBILEDEVICE3_UDID)) { throw 'Bind exact confirmed UDID' }; & .\.venv\Scripts\python.exe -m pymobiledevice3 developer core-device screen-capture screenshot screen.png --userspace
if ([string]::IsNullOrWhiteSpace($env:PYMOBILEDEVICE3_UDID)) { throw 'Bind exact confirmed UDID' }; & .\.venv\Scripts\python.exe -m pymobiledevice3 developer core-device universal-hid-service tap --userspace -- 32768 32768
if ([string]::IsNullOrWhiteSpace($env:PYMOBILEDEVICE3_UDID)) { throw 'Bind exact confirmed UDID' }; & .\.venv\Scripts\python.exe -m pymobiledevice3 developer core-device universal-hid-service type --userspace --char-delay 0.06 --inter-delay 0.04 -- 'Blue'
if ([string]::IsNullOrWhiteSpace($env:PYMOBILEDEVICE3_UDID)) { throw 'Bind exact confirmed UDID' }; & .\.venv\Scripts\python.exe -m pymobiledevice3 developer core-device universal-hid-service drag --userspace --duration 0.4 --steps 20 -- 32768 50000 32768 20000
if ([string]::IsNullOrWhiteSpace($env:PYMOBILEDEVICE3_UDID)) { throw 'Bind exact confirmed UDID' }; & .\.venv\Scripts\python.exe -m pymobiledevice3 developer core-device hid button home press --userspace
```

Center taps and drag endpoints illustrate syntax, not safe universal targets.
Coordinates are normalized unsigned integers 0..65535, not screenshot pixels.
Measure the current image/display dimensions and orientation; scale pixel
coordinates linearly to that range with a calculation tool and verify bounds.
Do not use `swipe` as a synonym for contact scrolling: upstream's gesture
`swipe` is pointer motion; use contact `drag` and verify the page changes.

Type only printable ASCII approved for that field. Inspect the entire string
before typing: unsupported characters may fail after a prefix already entered.
After focus/keyboard changes, capture again, recalculate clear/focus coordinates,
and verify field emptiness before replacement. Existing drafts must be preserved.
After typing, visually verify the **entire exact string**, including case and
unexpected duplication/autocorrection. Never add Enter/Send to these examples.

The local test typed `Blue`, then appended `tooth`, read back `Bluetooth` exactly,
and restored the original Settings search query. This is evidence of one safe
field, not permission to erase another field or proof of arbitrary Unicode.
