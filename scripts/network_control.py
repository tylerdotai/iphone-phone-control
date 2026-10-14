#!/usr/bin/env python3
"""Exact-peer Wi-Fi screenshot or one approved normalized tap. No auto-pairing."""
import argparse
import asyncio
import importlib.metadata
import ipaddress
import json
import logging
import os
from pathlib import Path
import re
import ssl
import sys


class Refusal(Exception):
    """Safe fixed-message operational refusal; never contains SDK data."""


class Parser(argparse.ArgumentParser):
    def error(self, message):
        # argparse normally echoes rejected values; do not disclose selectors.
        self.exit(2, 'Invalid arguments; use --help. No connection attempted.\n')


def arguments():
    parser = Parser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--udid', required=True, help='Human-confirmed exact device UDID')
    parser.add_argument('--host', required=True, help='Current literal private peer address')
    parser.add_argument('--port', required=True, type=int, help='Current RemotePairing bootstrap port')
    parser.add_argument('--output-dir', required=True, type=Path, help='Existing private task directory outside checkout')
    parser.add_argument('--tap', nargs=2, type=int, metavar=('X', 'Y'), help='One approved normalized tap (0..65535)')
    args = parser.parse_args()
    try:
        if not re.fullmatch(r'(?:[0-9a-fA-F]{8}-[0-9a-fA-F]{16}|[0-9a-fA-F]{40})', args.udid):
            raise ValueError
        if '%' in args.host:
            raise ValueError
        address = ipaddress.ip_address(args.host)
        ranges = ['10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16', '100.64.0.0/10', 'fc00::/7']
        if not any(address in ipaddress.ip_network(net) for net in ranges):
            raise ValueError
        if not 1 <= args.port <= 65535 or args.tap and any(not 0 <= n <= 65535 for n in args.tap):
            raise ValueError
        out = args.output_dir
        if out.is_symlink() or not out.is_dir():
            raise ValueError
        out = out.resolve(strict=True)
        if out.is_relative_to(Path(__file__).resolve().parents[1]):
            raise ValueError
        stat = out.stat()
        if stat.st_mode & 0o077 or hasattr(os, 'getuid') and stat.st_uid != os.getuid():
            raise ValueError
        names = ['before.png', 'after.png'] if args.tap else ['before.png']
        if any((out / name).exists() or (out / name).is_symlink() for name in names):
            raise ValueError
        args.output_dir = out
    except (ValueError, OSError):
        parser.error('invalid guarded selection or private output')
    return args, names


async def operate(args, files):
    # Lazy imports: all user-input/filesystem guards have already passed.
    import pymobiledevice3  # noqa: F401
    if sys.version_info < (3, 13) or not hasattr(ssl.SSLContext, 'set_psk_client_callback'):
        raise Refusal('Require Python 3.13+ with TCP PSK support.')
    if importlib.metadata.version('pymobiledevice3') != '11.29.0':
        raise Refusal('Require pymobiledevice3 11.29.0; no connection attempted.')
    from pymobiledevice3.remote import userspace_tunnel
    from pymobiledevice3.remote.tunnel_service import (
        create_core_device_tunnel_service_using_remotepairing,
        iter_remote_pair_records_by_identifier,
    )
    from pymobiledevice3.remote.core_device.screen_capture_service import ScreenCaptureService
    from pymobiledevice3.remote.core_device.hid_service import (
        touch_session, TOUCHSCREEN_STATE_CONTACT, TOUCHSCREEN_STATE_RELEASE,
    )
    if not any(identifier == args.udid for identifier, _, _ in iter_remote_pair_records_by_identifier()):
        raise Refusal('Existing exact-device RemotePairing record required; no new pairing attempted.')

    async def selected_provider(serial, autopair, remotepairing_fallback=True):
        if serial != args.udid or autopair:
            raise Refusal('Provider selection mismatch; stopped.')
        provider = await create_core_device_tunnel_service_using_remotepairing(
            args.udid, args.host, args.port, autopair=False,
        )
        if provider.remote_identifier != args.udid:
            await provider.close()
            raise Refusal('Provider identity mismatch; stopped.')
        return provider, None

    async def capture_png(capture, name):
        result = await capture.capture_screenshot()
        image = result['image']
        if not isinstance(image, bytes) or not image.startswith(b'\x89PNG\r\n\x1a\n'):
            raise Refusal('Capture was not PNG; stopped.')
        files[name].write(image)
        files[name].flush()

    original = userspace_tunnel._create_no_root_tunnel_provider
    userspace_tunnel._create_no_root_tunnel_provider = selected_provider
    try:
        async with userspace_tunnel.UserspaceRsdTunnel(serial=args.udid, autopair=False) as rsd:
            if rsd.udid != args.udid:
                raise Refusal('Developer tunnel identity mismatch; stopped.')
            async with ScreenCaptureService(rsd) as capture:
                await capture_png(capture, 'before.png')
                if args.tap:
                    async with touch_session(rsd) as hid:
                        try:
                            await hid.send_touchscreen(TOUCHSCREEN_STATE_CONTACT, *args.tap)
                            await asyncio.sleep(0.06)
                        finally:
                            await hid.send_touchscreen(TOUCHSCREEN_STATE_RELEASE, *args.tap)
                    await asyncio.sleep(0.6)
                    await capture_png(capture, 'after.png')
    finally:
        userspace_tunnel._create_no_root_tunnel_provider = original


def main():
    if sys.platform == 'win32':
        print('Native Windows network helper unsupported; use Linux or POSIX macOS. No connection attempted.', file=sys.stderr)
        return 2
    args, names = arguments()
    files = {}
    # Reserve every artifact exclusively before importing SDK or connecting.
    try:
        for name in names:
            fd = os.open(args.output_dir / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
            try:
                os.chmod(args.output_dir / name, 0o600)
                files[name] = os.fdopen(fd, 'wb')
            except BaseException:
                os.close(fd)
                raise
    except OSError:
        for stream in files.values():
            stream.close()
        print('Private output reservation refused; no connection attempted.', file=sys.stderr)
        return 2
    # SDK log messages can contain identities/keys; this dedicated process emits
    # only fixed diagnostics. Do not enable debug/traceback logging here.
    logging.disable(logging.CRITICAL)
    try:
        asyncio.run(asyncio.wait_for(operate(args, files), timeout=40))
    except Refusal as error:
        print(str(error), file=sys.stderr)
        return 1
    except (Exception, KeyboardInterrupt):
        print('Network operation stopped. Inspect private artifacts; do not retry input blindly.', file=sys.stderr)
        return 1
    finally:
        for stream in files.values():
            stream.close()
    print(json.dumps({'transport':'explicit authenticated private network; no USB fallback',
                      'artifacts':names, 'next':'Inspect decoded images and intended UI; restore approved temporary state.'}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
