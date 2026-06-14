"""C2b: core's client to the ECHO packet-shaper (core/echo_shaper_client.py).

Root-free + hermetic: a fake in-process JSON-RPC server over a real AF_UNIX socket placed at a
SHORT /tmp path (sidesteps the 104-char sun_path limit, so this runs in the DEFAULT suite, not
integration). Mirrors the fake-shim pattern in test_core_lock.py. Verifies the client's
protocol: handshake issues+caches the per-boot secret, the pf ops carry it, errors surface as
EchoShaperError, and an unreachable socket fails cleanly.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import shutil
import tempfile

import pytest
from core.echo_shaper_client import EchoShaperClient, EchoShaperError

SECRET = "a" * 64  # a stand-in 64-hex per-boot secret


class _FakeShaper:
    """Records every request and answers like the real shaper (handshake + pf ops)."""

    def __init__(self) -> None:
        self.requests: list[dict] = []
        self.handshakes = 0

    async def cb(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        line = await reader.readline()
        req = json.loads(line.decode())
        self.requests.append(req)
        method = req.get("method")
        params = req.get("params") or {}
        if method == "shaper.handshake":
            self.handshakes += 1
            resp: dict = {"result": {"secret": SECRET}}
        elif method == "shaper.ping":
            resp = {"result": {"pong": True}}
        elif method in ("shaper.anchor.load", "shaper.anchor.remove"):
            if params.get("secret") != SECRET:
                resp = {"error": {"code": -31007, "message": "secret required"}}
            else:
                resp = {"result": {"ok": True}}
        else:
            resp = {"error": {"code": -31002, "message": "capability missing"}}
        resp["jsonrpc"] = "2.0"
        resp["id"] = req.get("id")
        writer.write((json.dumps(resp) + "\n").encode())
        await writer.drain()
        writer.close()


@contextlib.asynccontextmanager
async def running_shaper():
    """Start a fake shaper on a short /tmp socket; yield (fake, client)."""
    sock_dir = tempfile.mkdtemp(dir="/tmp")
    sock = os.path.join(sock_dir, "es.sock")
    fake = _FakeShaper()
    server = await asyncio.start_unix_server(fake.cb, path=sock)
    try:
        yield fake, EchoShaperClient(sock)
    finally:
        server.close()
        await server.wait_closed()
        shutil.rmtree(sock_dir, ignore_errors=True)


async def test_ping_returns_pong() -> None:
    async with running_shaper() as (_fake, client):
        assert await client.ping() == {"pong": True}


async def test_handshake_returns_and_caches_secret() -> None:
    async with running_shaper() as (fake, client):
        assert await client.handshake() == SECRET
        await client.shape(100)  # reuses the cached secret — no second handshake
        assert fake.handshakes == 1


async def test_shape_handshakes_then_sends_secret_and_rate() -> None:
    async with running_shaper() as (fake, client):
        assert await client.shape(256) == {"ok": True}
        assert fake.handshakes == 1
        last = fake.requests[-1]
        assert last["method"] == "shaper.anchor.load"
        assert last["params"]["secret"] == SECRET
        assert last["params"]["rate_kbps"] == 256


async def test_unshape_sends_secret() -> None:
    async with running_shaper() as (fake, client):
        assert await client.unshape() == {"ok": True}
        last = fake.requests[-1]
        assert last["method"] == "shaper.anchor.remove"
        assert last["params"]["secret"] == SECRET


async def test_error_response_raises() -> None:
    async with running_shaper() as (_fake, client):
        with pytest.raises(EchoShaperError) as ei:
            await client.call("shaper.bogus")
        assert ei.value.code == -31002


async def test_unreachable_socket_raises() -> None:
    sock_dir = tempfile.mkdtemp(dir="/tmp")  # short path; never bound -> connect fails cleanly
    try:
        client = EchoShaperClient(os.path.join(sock_dir, "absent.sock"))
        with pytest.raises(EchoShaperError):
            await client.ping()
    finally:
        shutil.rmtree(sock_dir, ignore_errors=True)
