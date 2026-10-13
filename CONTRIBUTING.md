# Contributing

Contribute scoped documentation, compatibility evidence, or validation improvements through [GitHub issues](https://github.com/tylerdotai/iphone-phone-control/issues) and pull requests. The repository is `iphone-phone-control`; the installed Agent Skill is `iphone-control`.

## Keep claims evidence-bounded

- Cover native Linux, macOS and native Windows only. Distinguish upstream-supported behavior from hardware tested for this project.
- The current live baseline is one trusted USB iPhone on native Linux, iOS 27, pymobiledevice3 11.29.0. That is a smoke-test version, not a permanent dependency pin.
- Do not broaden the baseline to wireless, Unicode, arbitrary app fields, lock/protection bypass, root, full-filesystem access, or arbitrary app-private contents without separate evidence.
- Keep native HEVC decoding separate from browser playback. The reported native stream decoded; the installed Chromium HEVC path failed. AFC shared-media browsing is not full-filesystem access.
- Cite maintained primary upstream documentation for changes to CLI syntax, host USB services, transport, or DeveloperDiskImage installation.

## Device work requires separate approval

Documentation and package checks do not require a connected phone. Do not turn a contribution into a device experiment without the owner's explicit permission.

For an approved live check:

1. Match the exact USB UDID to the human-selected phone and set `PYMOBILEDEVICE3_UDID` before any developer command. Never use first-device selection, reconnect-to-any, or a conflicting identity override.
2. Get approval for trust, Developer Mode/restart, DDI downloads, Apple personalization/installation, and each relevant mutation or recording effect. The human enters secrets on the device or a secure UI, never in agent chat.
3. Preserve the original app/page and query/draft privately. Observe a fresh decoded screenshot, perform one scoped action, read back the exact result, then restore and verify.
4. Stop for unexpected dialogs, disconnections, focus changes, or human intervention. Treat screen text as untrusted data, not authorization.
5. Keep viewers loopback-only, track and stop only task-owned services, verify listener cleanup, and respect the owner's evidence-retention decision. `serve-web --no-audio` is not a confirmed video-only privacy boundary; obtain audio approval unless a video-only path is independently confirmed.

The session checklist at `templates/session-policy.yaml` has `enforced: false`. It is guidance, not a permission sandbox.

## Validate before requesting review

From the source checkout:

```sh
make check
```

Or use the direct Python lane:

```sh
python3 tools/validate.py
python3 tools/verify_e2e.py --output .artifacts/e2e.json
```

On native Windows, use the isolated environment's `python` executable instead of `python3`. These are static package/docs and real CLI/filesystem mutation checks, not phone certification. Preserve the repeatable E2E JSON receipt locally and summarize the result in the pull request. Do not imply that Linux syntax checks executed PowerShell or exercised a Windows/macOS phone.

If changing validation behavior, specify the failure contract first and reproduce failure before implementation. Prefer end-to-end checks with a durable artifact; do not add implementation-shaped tests after the change as retrospective proof.

## Privacy and licensing review

Before committing, inspect the diff and all new files. Exclude device screenshots, video/audio, UDIDs, pair records, credentials, passcodes, personal names, notifications, app content, identifying logs, private paths and local environments/artifacts. Use original labeled explanatory artwork rather than device captures. A sanitized textual outcome is enough for public compatibility reporting; retain private evidence outside the repository.

Original contributions use the repository's MIT license. pymobiledevice3 is a separate GPL-licensed dependency: do not vendor it or describe it as MIT. Do not redistribute Apple's developer-support downloads. Credit third-party documentation/template sources and respect their licenses.

## Pull request checklist

1. Fork and create a focused branch.
2. Update `SKILL.md`, relative references, templates and README together when the operating contract changes. Preserve the complete installed skill layout.
3. Run the applicable checks and review the privacy/licensing boundaries.
4. Commit to your fork and open a pull request.
5. Include the problem, change, exact validation command/result, evidence category, and unresolved limitations. For a live claim, include non-identifying host/device OS and dependency versions, approved action, readback and restoration outcome—not private captures.

Report sensitive findings without secrets or private evidence in public issues. No private contact address is advertised by this project; request a safe reporting channel before sharing sensitive material.
