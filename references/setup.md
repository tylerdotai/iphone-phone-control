# Host setup and trust gates

## Before changing anything

Work on the host that already owns the USB cable, not a separate container.
Confirm OS, Python version, installed pymobiledevice3 version, USB service,
permissions, and iOS version. Read the current installation and tunnel sources
below. Do not overwrite an existing environment or upgrade packages silently.
Use a dedicated terminal/environment; record changes and task-owned processes.
Upstream currently documents Python 3.9+; recheck package requirements before
installation. The included Wi-Fi helper separately requires Python 3.13+ and pins
pymobiledevice3 11.29.0 because it uses a version-specific provider seam. See
[Wi-Fi bootstrap and control](wifi.md).

| Host | USB prerequisites | Evidence status |
| --- | --- | --- |
| Linux | Native usbmuxd service; approved distribution package/service/USB permission fixes if missing | One trusted USB and same-LAN Wi-Fi iPhone exercised |
| macOS | System usbmuxd; Python in an isolated environment | Upstream-documented, not tested here |
| Native Windows | Apple USB drivers and Apple Mobile Device Service; upstream recommends Apple's classic iTunes installer | Upstream-documented, not tested here |

Do not replace working Apple services automatically. Driver installs and service
changes require approval. Windows Wi-Fi discovery depends on the Apple package;
USB support is not a wireless-control test. Do not alter PowerShell execution
policy: call the virtual environment's interpreter directly if activation fails.

## Isolated Python install (only after approval)

Run in a chosen empty task directory. These host-only commands do not select or
operate a device. If `.venv` exists, inspect it or choose another directory.

Bash on Linux/macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install "pymobiledevice3==11.29.0"
source .venv/bin/activate
python -m pip show pymobiledevice3
```

Native Windows PowerShell:

```powershell
py -3 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install "pymobiledevice3==11.29.0"
& .\.venv\Scripts\python.exe -m pip show pymobiledevice3
```

For Windows command examples in commands.md, use this interpreter path rather
than assuming a global `python` points to the new environment.

## Human prerequisites and developer support

1. Connect the selected iPhone by USB. Have the human unlock it and approve Trust
   locally if needed. Pairing persists host/device credentials; obtain consent.
2. Have the human enable Developer Mode in Settings > Privacy & Security when
   required. Explain reduced security and the restart; obtain approval first.
   The human completes reboot confirmation and passcode entry. If the toggle is
   absent, inspect current upstream/Apple guidance; do not claim a Mac is always
   required, bypass security, or initiate unrelated pairing/install steps.
3. Bind the exact device using commands.md before any device-facing command.
4. Inspect support status/help. If compatible support is absent, separately
   approve `mounter auto-mount`: it may download/cache a Developer Disk Image
   (DDI), contact Apple for device-specific personalization, and mount or install
   developer support on the phone. On the tested iOS 27 path it installed Cryptex1
   support rather than merely attaching a harmless host disk image.
5. Verify support readiness by an inspected screenshot. After reboot, recheck
   readiness; do not assume support persists or uninstall another tool's image.

Newer CoreDevice control needs neither a Mac nor WebDriverAgent (WDA) as a
universal prerequisite. Actual service availability varies by iOS/device.
For iOS 17.4+ USB, prefer explicit `--userspace` for an in-process no-admin tunnel.
iOS 17.0–17.3.1 needs different transport: upstream documents macOS native tunnel
and privileged tunneld/additional drivers on Linux/Windows. Do not use these
examples blindly there; consult current guidance and obtain privilege/service
approval. A tunnel working does not prove this skill's HID services exist.

## Maintained primary sources

- [Installation and platform prerequisites](https://doronz88.github.io/pymobiledevice3/installation/)
- [Tunnel support matrix](https://doronz88.github.io/pymobiledevice3/guides/ios17-tunnels/)
- [DDI and CoreDevice CLI recipes](https://doronz88.github.io/pymobiledevice3/guides/cli-recipes/)
- [Apple Developer Mode](https://developer.apple.com/documentation/xcode/enabling-developer-mode-on-a-device)

These links describe upstream behavior, not additional local device tests.
