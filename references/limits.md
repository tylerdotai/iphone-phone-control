# Evidence, limits, and troubleshooting gates

## Tested versus upstream-supported

| Capability | Evidence |
| --- | --- |
| Linux trusted USB, human-enabled Developer Mode | Exercised on one iPhone running iOS 27 |
| Isolated pymobiledevice3, DDI installation | Tested version 11.29.0; Apple-personalized Cryptex1 installed by auto-mount |
| CoreDevice screenshot, normalized tap, contact drag, Home button | Exercised with visible readback |
| Printable ASCII input | Exact `Blue` + `tooth` -> `Bluetooth` readback; original query restored |
| Native HEVC video capture/decoding | 163 distinct decoded frames in the local test |
| Linux headless-browser HEVC rendering | Failed: installed browser reported unsupported HEVC |
| macOS and native Windows | Platform/transport support documented upstream; no device tests here |
| iPhone wireless and arbitrary Unicode input | Not tested here |

These are supplied prior-test results, not tests performed by loading this
payload. No device identifiers, private receipts, accounts, personal paths, or
screenshots are distributed. Version 11.29.0 labels that test only; recheck current
help/source and requirements instead of treating it as a required version pin.
Do not generalize the successful device/OS combination to every iPhone/iOS.

## Media consent and fallback

Prefer individual screenshots unless continuous video is requested. Touch and
keyboard commands may temporarily start a media stream for HID authentication;
disclose this before approval and inspect current code's media/audio behavior.
Do not assume HID is media-free or that it cannot affect camera/microphone use.

Native HEVC decoding and browser playback are separate acceptance criteria.
Prove capture, increasing decoded frames, and visible motion independently.
A stream handshake or supported-codec advertisement is not a live image test.
If the browser lacks HEVC, use inspected screenshots; do not promise universal
browser mirroring or install a decoder/browser silently.

`serve-web --no-audio` does **not** guarantee a video-only backend. In the local
test its backend still attempted an AAC-ELD audio decoder, which failed because
that decoder was macOS-only; no audio artifacts were produced. Do not recommend
that flag as audio exclusion. If video-only operation is required, inspect the
current video-only API/capture route and verify that it requests no audio before
using it. This payload deliberately supplies no web-stream launch command.

Camera/microphone apps can conflict with screen mirroring. Stop task-owned media
sessions before approved camera/microphone work; re-observe after any media
transition. Do not quit human-owned apps or stop unrelated services automatically.
If a separate approved workflow starts a server, bind loopback only, record its
process/listener identity, keep clipboard sync off unless approved, and verify
that exact listener is gone after cleanup.

## Failure gates

- Device absent/trust refused: check the cable-owning host's USB service and
  human-local unlock/trust. Do not scan another host or silently pair a new phone.
- Wrong device, reconnect, or selector uncertain: stop; repeat exact binding.
- Missing DDI/developer service: inspect compatibility and Developer Mode; ask
  before downloads, personalization, install, restart, or elevated transport.
- Accepted HID report but no screen change: capture again and diagnose focus,
  coordinate normalization, orientation, and service availability; no blind retry.
- Keyboard shifted the field: discard old clear/focus coordinates. Verify actual
  emptiness and new focus before typing. Unexpected text means stop, not append.
- Human changed the app: stop before any typing; request a fresh handoff.
- Black/protected screenshot: report limited visibility; do not bypass locks or
  protections. Root, full filesystem, protected-screen capture, and lock bypass
  are not supplied or guaranteed. App-container APIs are not unrestricted access.

Read [upstream CLI recipes](https://doronz88.github.io/pymobiledevice3/guides/cli-recipes/)
and [tunnel guidance](https://doronz88.github.io/pymobiledevice3/guides/ios17-tunnels/)
for current service-specific limits. Report new failures without relabeling an
upstream-supported platform as locally validated.
