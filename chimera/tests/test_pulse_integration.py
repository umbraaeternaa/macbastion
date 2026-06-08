"""PULSE daemon integration (module-only slice) — in-process vs live core.

In-process (Python): PulseClient runs as an asyncio task on the same loop; the socket
layer is exercised end to end against a live core.Server. Registers on core.sock, serves
pulse.status / pulse.weights.set via the 4A router, heartbeats. RED until the client is
implemented. Marked integration, deselected by default (needs a short --basetemp,
AF_UNIX path-too-long).
"""

import asyncio

import pytest
from core.broker import EventBroker
from core.config import CoreConfig
from core.envelope import Response, parse
from core.lifecycle import Lifecycle
from core.registry import Registry
from core.server import Server
from core.tokens import TokenIssuer
from pulse.baseline import BaselineStore
from pulse.client import PulseClient

pytestmark = pytest.mark.integration


def _make_core(tmp_path):
    config = CoreConfig.model_validate({"socket_dir": str(tmp_path)})
    broker = EventBroker()
    lifecycle = Lifecycle(config, broker)
    registry = Registry(lifecycle, broker)
    server = Server(config, registry, lifecycle, broker, TokenIssuer())
    return server, registry, broker


async def _wait(pred, timeout_s=5.0):
    for _ in range(int(timeout_s / 0.05)):
        if pred():
            return True
        await asyncio.sleep(0.05)
    return False


async def _roundtrip(sock, line, timeout_s=5.0):
    reader, writer = await asyncio.open_unix_connection(str(sock))
    try:
        writer.write(line.encode())
        await writer.drain()
        raw = await asyncio.wait_for(reader.readline(), timeout=timeout_s)
        msg = parse(raw.decode())
        assert isinstance(msg, Response)
        return msg
    finally:
        writer.close()
        await writer.wait_closed()


def _client(tmp_path):
    store = BaselineStore(tmp_path / "baseline.db", tmp_path / "baseline.key")
    return PulseClient(tmp_path, store, session_start="2026-06-12T14:00:00")


async def test_pulse_registers(tmp_path):
    server, registry, _ = _make_core(tmp_path)
    await server.start()
    task = asyncio.create_task(_client(tmp_path).run())
    try:
        assert await _wait(lambda: registry.is_registered("pulse"))
    finally:
        task.cancel()
        await server.stop()


async def test_pulse_status_roundtrip(tmp_path):
    server, registry, _ = _make_core(tmp_path)
    await server.start()
    task = asyncio.create_task(_client(tmp_path).run())
    try:
        assert await _wait(lambda: registry.is_registered("pulse"))
        resp = await _roundtrip(
            tmp_path / "core.sock", '{"jsonrpc":"2.0","id":1,"method":"pulse.status"}\n'
        )
        assert resp.error is None
        for k in ("score", "mode", "baseline_ready", "session_minutes"):
            assert k in resp.result
        assert resp.result["mode"] == "normal"  # uncalibrated -> normal (fail-open §8)
        assert resp.result["baseline_ready"] is False
        assert 0.0 <= resp.result["score"] <= 1.0
    finally:
        task.cancel()
        await server.stop()


async def test_pulse_weights_set_roundtrip(tmp_path):
    server, registry, _ = _make_core(tmp_path)
    await server.start()
    task = asyncio.create_task(_client(tmp_path).run())
    try:
        assert await _wait(lambda: registry.is_registered("pulse"))
        resp = await _roundtrip(
            tmp_path / "core.sock",
            '{"jsonrpc":"2.0","id":2,"method":"pulse.weights.set",'
            '"params":{"w_a":0.5,"w_b":0.3,"w_c":0.2}}\n',
        )
        assert resp.error is None
        assert "config" in resp.result
    finally:
        task.cancel()
        await server.stop()


async def test_pulse_weights_set_rejects_bad_sum(tmp_path):
    server, registry, _ = _make_core(tmp_path)
    await server.start()
    task = asyncio.create_task(_client(tmp_path).run())
    try:
        assert await _wait(lambda: registry.is_registered("pulse"))
        resp = await _roundtrip(
            tmp_path / "core.sock",
            '{"jsonrpc":"2.0","id":3,"method":"pulse.weights.set",'
            '"params":{"w_a":0.9,"w_b":0.3,"w_c":0.2}}\n',
        )
        assert resp.error is not None  # sum != 1.0 -> invalid params
    finally:
        task.cancel()
        await server.stop()
