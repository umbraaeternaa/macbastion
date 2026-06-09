"""core.lock operator command -> privileged shim (P4c).

No-shim case is a pure unit (default suite). Forwarding to a fake shim and the live shim
use real AF_UNIX sockets (integration, short --basetemp). RED until _handle_lock lands.
"""

import asyncio
import json
import os

import pytest
from core.broker import EventBroker
from core.config import CoreConfig
from core.envelope import Request
from core.errors import ChimeraError
from core.lifecycle import Lifecycle
from core.registry import Registry
from core.server import Server
from core.shim_client import ShimClient
from core.tokens import TokenIssuer


def _server(tmp_path, shim_client=None):
    config = CoreConfig.model_validate({"socket_dir": str(tmp_path)})
    broker = EventBroker()
    lifecycle = Lifecycle(config, broker)
    registry = Registry(lifecycle, broker)
    return Server(config, registry, lifecycle, broker, TokenIssuer(), shim_client=shim_client)


def _lock_req():
    return Request(jsonrpc="2.0", id=1, method="core.lock", params=None)


async def _fake_shim(sock_path, responder):
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


async def test_core_lock_without_shim_precondition(tmp_path):
    server = _server(tmp_path, shim_client=None)
    conn = server.new_connection()
    resp = await server.handle_command(_lock_req(), conn)
    assert resp.error is not None
    assert resp.error["code"] == ChimeraError.PRECONDITION_FAILED


@pytest.mark.integration
async def test_core_lock_forwards_to_shim(tmp_path):
    sock = tmp_path / "shim.sock"
    fake = await _fake_shim(sock, lambda req: {"result": {"ok": True, "noop": True}})
    try:
        server = _server(tmp_path, shim_client=ShimClient(str(sock)))
        conn = server.new_connection()
        resp = await server.handle_command(_lock_req(), conn)
        assert resp.error is None
        assert resp.result == {"ok": True, "noop": True}
    finally:
        fake.close()
        await fake.wait_closed()


@pytest.mark.integration
@pytest.mark.skipif(
    not os.path.exists("/var/run/chimera-shim.sock"), reason="live shim not installed"
)
async def test_core_lock_live_shim(tmp_path):
    server = _server(tmp_path, shim_client=ShimClient("/var/run/chimera-shim.sock"))
    conn = server.new_connection()
    resp = await server.handle_command(_lock_req(), conn)
    assert resp.error is None
    assert resp.result.get("ok") is True
