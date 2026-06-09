"""Core ShimClient integration (P4b) — against a fake shim, plus the LIVE shim if it is
installed. Marked integration (real AF_UNIX); needs a short --basetemp. RED until
ShimClient.call lands.
"""

import asyncio
import json
import os

import pytest
from core.shim_client import ShimClient, ShimError

pytestmark = pytest.mark.integration


async def _fake_shim(sock_path, responder):
    """A one-shot fake shim: read one NDJSON request, reply with responder(req)."""

    async def cb(reader, writer):
        line = await reader.readline()
        req = json.loads(line.decode())
        resp = responder(req)
        resp.setdefault("jsonrpc", "2.0")
        resp["id"] = req.get("id")
        writer.write((json.dumps(resp) + "\n").encode())
        await writer.drain()
        writer.close()

    return await asyncio.start_unix_server(cb, path=str(sock_path))


async def test_ping_returns_result(tmp_path):
    sock = tmp_path / "shim.sock"
    server = await _fake_shim(sock, lambda req: {"result": {"pong": True}})
    try:
        assert await ShimClient(socket_path=str(sock)).ping() == {"pong": True}
    finally:
        server.close()
        await server.wait_closed()


async def test_lock_returns_noop(tmp_path):
    sock = tmp_path / "shim.sock"
    server = await _fake_shim(sock, lambda req: {"result": {"ok": True, "noop": True}})
    try:
        assert await ShimClient(socket_path=str(sock)).lock() == {"ok": True, "noop": True}
    finally:
        server.close()
        await server.wait_closed()


async def test_error_response_raises(tmp_path):
    sock = tmp_path / "shim.sock"
    server = await _fake_shim(sock, lambda req: {"error": {"code": -31002, "message": "unknown"}})
    try:
        with pytest.raises(ShimError) as ei:
            await ShimClient(socket_path=str(sock)).call("shim.bogus")
        assert ei.value.code == -31002
    finally:
        server.close()
        await server.wait_closed()


async def test_unreachable_raises(tmp_path):
    with pytest.raises(ShimError):
        await ShimClient(socket_path=str(tmp_path / "nope.sock")).ping()


@pytest.mark.skipif(
    not os.path.exists("/var/run/chimera-shim.sock"), reason="live shim not installed"
)
async def test_live_shim_if_present():
    result = await ShimClient(socket_path="/var/run/chimera-shim.sock").ping()
    assert result.get("pong") is True
