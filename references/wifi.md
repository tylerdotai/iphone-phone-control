# Wi-Fi control: trusted USB bootstrap, explicit authenticated peer

## Supported scope and prerequisites

Same-LAN Wi-Fi screenshot, normalized HID tap, and restoration were exercised
on native Linux with one iPhone running iOS 27.0.1 and pymobiledevice3 11.29.0,
with USB physically disconnected. The authenticated RemotePairing provider and
root-free in-process RSD path produced decoded screenshots and fresh UI readback.
This does not establish compatibility with every iPhone, iOS, app or host.
The network helper supports Linux and POSIX macOS only. Linux is device-tested;
macOS transport is upstream-documented and the helper is untested there.
Native Windows network helper unsupported: POSIX privacy checks do not validate
NTFS ACLs. It refuses Windows before argument/file guards, SDK import or network
access. Windows USB and trusted USB bootstrap guidance remains upstream-documented,
not device-tested; it does not establish Windows helper support.
The verified phone/controller topology is home Wi-Fi. Same-LAN addresses and explicit Tailscale addresses were both exercised; no cellular-only or off-LAN topology is claimed.

Use Python **3.13+** with `ssl.SSLContext.set_psk_client_callback` and
**pymobiledevice3==11.29.0** for the included helper. Its SDK integration uses a
private provider-factory seam; other SDK versions are refused, not silently
adapted. Version 11.29.0's userspace stack explicitly starts a TCP PSK tunnel.
Do not install another PSK library or elevate privileges as a fallback.
The upstream general CLI's Python requirement is different from this helper's.

Follow [setup](setup.md) first: approved trusted USB pairing, Developer Mode,
restart/local confirmation, compatible personalized developer support, private
host credentials and explicit full UDID binding. Do not copy/export pair records.
Approve Wi-Fi connection enablement and persistent RemotePairing separately.
The helper never bootstraps pairing or installs developer support.

Use the same SDK user-data home and environment used for trusted USB bootstrap,
including the same `XDG_DATA_HOME` when set. A different shell or desktop runtime
can select a different SDK credential cache even with the same interpreter.
A missing record is a stop condition: restore the original process-scoped
environment, not new pairing. Do not copy/export pairing keys or implicitly
search unrelated credential directories.

## 1. Bootstrap only over the selected trusted USB connection

Bind `PYMOBILEDEVICE3_UDID` through [exact-device selection](commands.md),
with the human-confirmed USB UDID and no conflicting transport defaults.
In the selected dedicated environment, define the guarded `iphone` wrapper:

Bash:

```bash
iphone() {
  if [ -z "${PYMOBILEDEVICE3_UDID:-}" ]; then
    printf '%s\n' 'Stop: bind the exact USB device first.' >&2
    return 1
  fi
  command python -m pymobiledevice3 "$@"
}
```

Native PowerShell (set `$IphonePython` to the isolated interpreter's absolute path):

```powershell
function iphone {
    if ([string]::IsNullOrWhiteSpace($env:PYMOBILEDEVICE3_UDID)) {
        throw 'Stop: bind the exact USB device first.'
    }
    & $IphonePython -m pymobiledevice3 @args
    if ($LASTEXITCODE -ne 0) { throw 'Device command failed; stop and inspect' }
}
```

Record the original Wi-Fi connection state privately before changing it:

```sh
iphone lockdown wifi-connections
iphone lockdown wifi-connections on
iphone lockdown remotepairing --pair
```

The last command persists a RemotePairing record over already-trusted lockdown.
It can be promptless; promptless is not consent. Handshake output contains
private device information. Inspect it locally, never publish it. Re-read
`iphone lockdown wifi-connections` to confirm the approved state change.
Complete and visually verify USB developer support before removing the cable.

## 2. Discover the current same-LAN endpoint, then bind explicitly

Have the human disconnect USB physically and confirm both host and phone are
on the approved LAN. A LAN with client isolation, blocked discovery or missing
routes may not work. Do not change firewall/router/network settings silently.
After approval for bounded LAN discovery, run:

```sh
python -m pymobiledevice3 bonjour mobdev2 --timeout 4
python -m pymobiledevice3 bonjour remotepairing --timeout 4
```

On native PowerShell, replace `python` with `& $IphonePython`.
These commands are discovery, not target authorization. Match the exact
`UniqueDeviceID` and `ip` from authenticated mobdev2 discovery to the already
human-confirmed phone. Match that address to `hostname` and the **current**
`port` in RemotePairing discovery. RemotePairing advertisements alone do not
prove identity. Stop on absent, ambiguous or inconsistent matches. Never choose
the first entry. Do not probe arbitrary hosts/ports or broaden discovery.

The bootstrap port can change after restart/reconnect. It is not a persistent
RSD service port, a port learned from an older tunnel, or a fixed universal port.
Keep the full UDID, address and current port in private shell variables `UDID`,
`HOST` and `PORT`; fill them from these matched observations, never from examples.
The helper accepts literal private endpoints only (not DNS names, public,
loopback, multicast, link-local or scoped addresses). Private addressing alone
is not authorization: exact pairing and authenticated provider/RSD identities
must also match. There is no USB, Bonjour, arbitrary-device or public fallback.

## Optional Tailscale addressing while the phone stays on Wi-Fi

The actual included helper was also exercised on Linux through the phone's literal Tailscale address: authenticated screenshots, approved Settings navigation, visual readback and restoration succeeded with USB physically absent. Phone and controller were on home Wi-Fi. This verifies that endpoint path, not cellular-only or away-from-home operation.

Keep both clients online in the same authorized tailnet, with already-approved incoming access and policy. Confirm the intended phone's peer address locally; keep the exact UDID and existing RemotePairing record from bootstrap. Set `HOST` to that literal peer address and `PORT` to the current **RemotePairing bootstrap port** learned through the matched discovery above. Use the same helper invocation and private-output guards below. The helper authenticates the selected device and never silently falls back to a LAN address or USB.

Tailscale does not carry Bonjour discovery or freeze Apple's ports. A stale port is not permission to scan or select another peer. Reestablish approved local discovery/diagnostics before reconnecting. Do not confuse the bootstrap port with a USB-inner RSD port or a newly allocated tunnel data port. Do not change ACLs, firewalls, pairing, or other network controls implicitly.

Cellular-only developer connectivity is tracked in [issue #1](https://github.com/tylerdotai/iphone-phone-control/issues/1). It is not a supported release claim.

## 3. Capture, inspect, approve one tap, then read back

Set `HELPER` to the absolute path of `scripts/network_control.py` in the installed
skill or checkout. Use the selected isolated interpreter, not a global SDK.
Choose an existing **new, task-owned private directory outside the checkout**
for each invocation. On Linux/macOS, create it with mode 0700; the helper checks
ownership/private permission bits and refuses symlinks and existing artifact names.
Native Windows cannot run this helper; owner-only ACLs do not make its POSIX
mode check valid on NTFS. Do not loosen the private-directory guard.

Bash (set the private variables above and `OUT` to that directory):

```bash
python "${HELPER:?Set installed helper path}" --udid "${UDID:?Bind exact phone}" --host "${HOST:?Bind current private peer}" --port "${PORT:?Bind current bootstrap port}" --output-dir "${OUT:?Choose private output}"
```

Open and decode `before.png`. Confirm app/orientation, target, dimensions and
starting state. Get approval for the exact benign tap. Derive normalized X/Y
integers in 0..65535 from the fresh image using the README calculator. Do not
paste stale or universal coordinates. Choose another new private `OUT` directory:

```bash
python "${HELPER:?Set installed helper path}" --udid "${UDID:?Bind exact phone}" --host "${HOST:?Bind current private peer}" --port "${PORT:?Bind current bootstrap port}" --output-dir "${OUT:?Choose new private output}" --tap "${X:?Review normalized X}" "${Y:?Review normalized Y}"
```

The helper captures `before.png`, sends one contact/release, and captures
`after.png`. Its pre-tap capture is evidence, **not an approval prompt**: the
operator must already have inspected the current UI and approved the target.
If the phone changes between observation and invocation, stop. Do not queue
input. Touch authentication can temporarily start media; approve those side
effects under [limits](limits.md), and do not claim a screen-only/audio guarantee.

On supported hosts, the helper writes files exclusively with POSIX mode 0600, reserves all output names
before connecting, and keeps partial/empty evidence private on failure. It uses
an existing RemotePairing record, `autopair=False`, exact authenticated provider
and RSD checks, and a process-scoped provider override restored in `finally`.
It closes services/tunnel and attempts release in `finally`, even if contact
fails. A release failure can leave uncertain input state: stop for the human;
never automatically retry. A 40-second operation timeout stops the workflow.
Diagnostics suppress SDK logs and exception contents, not a confidentiality
sandbox around an untrusted dependency or agent.

No automatic UI-success claim is emitted. Decode and inspect both images,
verify the intended effect, restore only approved temporary navigation through
freshly observed one-tap calls, and confirm restoration with another screenshot.
No typing, submission, shell, service forwarding, daemon or broad automation is
provided by this network helper. Do not use the USB `--userspace` CLI lane as a
wireless substitute: in this SDK its default provider starts with USB selection.

## 4. Disconnect and revoke only when separately approved

Finishing the helper closes its process-owned transport; no persistent helper
server or privileged host network interface is installed. Exiting does **not**
revoke persistent Wi-Fi/trust/RemotePairing credentials. Keep or remove private
artifacts only under the owner's retention choice.

To restore Wi-Fi enablement, reconnect the exact trusted USB phone, recheck its
identity, obtain approval, and use `iphone lockdown wifi-connections off` only
if this restores the recorded starting state. Read the state again. Do not
disable a preexisting enabled setting by default.

For credential revocation, stop this session, explain the impact on other trusted
workflows, and have the human choose the appropriate current Apple trust reset
or upstream exact-record removal procedure. Verify refusal of the revoked peer
in a separately authorized session. Do not bulk-delete pairing directories,
copy secrets, claim Wi-Fi-off erased trust, or uninstall developer support.

## Offline checks and live acceptance

`make check` runs real subprocess argument/filesystem/package contracts with
inert SDK fixtures and a network socket barrier. Fixtures do not prove hardware
behavior. The source checkout includes the preimplementation failure contract at
`tools/network-cli-contract.md` (not part of the installed payload).
Live acceptance of a changed helper requires its actual entrypoint, USB absent,
fresh decoded PNGs, one approved benign tap, exact UI readback and restoration.
Never replace that gate with fixture success or SDK protocol acknowledgements.

Primary SDK source at the pinned release:
- [Userspace provider and TCP tunnel](https://github.com/doronz88/pymobiledevice3/blob/v11.29.0/pymobiledevice3/remote/userspace_tunnel.py)
- [RemotePairing and PSK](https://github.com/doronz88/pymobiledevice3/blob/v11.29.0/pymobiledevice3/remote/tunnel_service.py)
- [USB bootstrap commands](https://github.com/doronz88/pymobiledevice3/blob/v11.29.0/pymobiledevice3/cli/lockdown.py)
- [Bounded discovery](https://github.com/doronz88/pymobiledevice3/blob/v11.29.0/pymobiledevice3/cli/bonjour.py)
