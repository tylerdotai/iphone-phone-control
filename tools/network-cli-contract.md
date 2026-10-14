# Network helper contract (specified before implementation)

Boundary: real helper subprocess, argparse, private filesystem, and installed payload.
No phone/network operations are permitted in this lane. A subprocess audit hook
refuses sockets. SDK fixtures exist only because live device operations are out of
scope; fixture PNG bytes are inert and never hardware evidence.

Known failures and acceptance criteria:
- Missing helper or payload/reference; incomplete/stale/extra/traversing archives.
- Missing/empty/malformed UDID (modern 8-16 hexadecimal or legacy 40 hexadecimal),
  host (literal RFC1918 IPv4, ULA IPv6, or shared private endpoint only), or port
  (integer 1..65535); public, loopback, multicast, hostname, and scoped-IP refusal.
- Missing/nonprivate/symlink/checkout output directory; existing/symlink artifacts;
  no overwrites. Guards run before SDK imports or socket use.
- Unknown operation/option; partial tap, noninteger/out-of-range coordinates;
  screenshot and explicit normalized tap are the only actions.
- Unsupported Python (<3.13), missing/wrong SDK (exact 11.29.0), missing existing
  RemotePairing record: sanitized refusal, no pairing, fallback or disclosure.
- Provider selector mismatch, provider identity mismatch, RSD identity mismatch:
  no capture/input; exact explicit endpoint; autopair=False everywhere.
- SDK connect/capture/touch/release exceptions, malformed PNG, timeout: sanitized
  nonzero result, no traceback/identifiers/addresses/credentials.
- Every acquired resource closes; provider factory restored even on failure.
  Contact has a release in finally, including failed contact transmission.
- Screenshot writes before.png; tap writes before.png and after.png, exclusive
  mode 0600. Existing files refuse before SDK use. Partial evidence is retained
  privately on failure, never labelled passed input or verified UI.
- Report transport/artifacts without identity data; always require visual inspection.
  No text entry, submission, service forwarding, persistent daemon or host changes.

Regenerate: `python3 tools/verify_network_cli.py --output .artifacts/network-cli.json`.
Preserve the preimplementation RED separately in `.artifacts/network-cli-red.json`.
