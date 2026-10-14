"""Offline SDK stand-in loaded only by the subprocess contract harness.

Not a device simulator or evidence of device behavior. Sockets are forbidden.
"""
import contextlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import types
import binascii
import struct
import zlib


def record(event):
    with Path(os.environ['FIXTURE_EVENTS']).open('a') as stream:
        stream.write(json.dumps(event) + '\n')


def audit(event, args):
    if event in {'socket.connect', 'socket.bind', 'socket.getaddrinfo'} or event == 'socket.__new__' and args[1] != 1:
        raise RuntimeError('offline fixture forbids network sockets')


sys.addaudithook(audit)
mode = os.environ.get('FIXTURE_MODE', 'ok')
original_version = importlib.metadata.version
importlib.metadata.version = lambda name: ('0.0.0' if mode == 'version' else '11.29.0') if name == 'pymobiledevice3' else original_version(name)


def module(name):
    m = types.ModuleType(name)
    m.__path__ = []
    sys.modules[name] = m
    return m


for name in ['pymobiledevice3', 'pymobiledevice3.remote', 'pymobiledevice3.remote.core_device']:
    module(name)
u = module('pymobiledevice3.remote.userspace_tunnel')
t = module('pymobiledevice3.remote.tunnel_service')
s = module('pymobiledevice3.remote.core_device.screen_capture_service')
h = module('pymobiledevice3.remote.core_device.hid_service')
record({'event': 'sdk-import'})
SECRET = 'SENSITIVE_SENTINEL'


async def original(*args, **kwargs):
    raise RuntimeError('USB fallback forbidden')


u._create_no_root_tunnel_provider = original


class Provider:
    def __init__(self, target):
        self.remote_identifier = 'wrong' if mode == 'provider-id' else target

    async def close(self):
        record({'event': 'provider-close'})


async def create(target, host, port, autopair=True):
    record({'event': 'connect', 'target': target, 'host': host, 'port': port, 'autopair': autopair})
    if mode == 'connect':
        raise RuntimeError(SECRET)
    return Provider(target)


t.create_core_device_tunnel_service_using_remotepairing = create
t.iter_remote_pair_records_by_identifier = lambda: iter([] if mode == 'record' else [('00000000-0000000000000000', None, {})])


class Tunnel:
    def __init__(self, serial, autopair):
        self.serial, self.autopair = serial, autopair
        self.provider = None

    async def __aenter__(self):
        try:
            self.provider, lockdown = await u._create_no_root_tunnel_provider('wrong' if mode == 'selector' else self.serial, self.autopair)
            return types.SimpleNamespace(udid='wrong' if mode == 'rsd-id' else self.serial)
        except BaseException:
            if self.provider:
                await self.provider.close()
            raise

    async def __aexit__(self, *args):
        await self.provider.close()
        record({'event': 'tunnel-close'})


u.UserspaceRsdTunnel = Tunnel


def chunk(kind, body):
    return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', binascii.crc32(kind + body) & 0xffffffff)


PNG = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(b'\x00\x00\x00\x00\x00')) + chunk(b'IEND', b'')


class Capture:
    def __init__(self, rsd):
        pass

    async def __aenter__(self):
        record({'event': 'capture-open'})
        return self

    async def __aexit__(self, *args):
        record({'event': 'capture-close'})

    async def capture_screenshot(self):
        record({'event': 'capture'})
        if mode == 'capture':
            raise RuntimeError(SECRET)
        return {'image': b'bad' if mode == 'png' else PNG}


s.ScreenCaptureService = Capture
h.TOUCHSCREEN_STATE_CONTACT = 1
h.TOUCHSCREEN_STATE_RELEASE = 0


class Hid:
    async def send_touchscreen(self, state, x, y):
        record({'event': 'touch', 'state': state, 'x': x, 'y': y})
        if mode == 'touch' and state == 1 or mode == 'release' and state == 0:
            raise RuntimeError(SECRET)


@contextlib.asynccontextmanager
async def touch_session(rsd):
    record({'event': 'hid-open'})
    try:
        yield Hid()
    finally:
        record({'event': 'hid-close'})


h.touch_session = touch_session


def final_check():
    record({'event': 'factory-restored', 'ok': u._create_no_root_tunnel_provider is original})


import atexit
atexit.register(final_check)
