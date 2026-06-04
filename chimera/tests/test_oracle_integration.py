"""ORACLE daemon integration (observe-first slice) — in-process vs live core.

In-process (not subprocess): ORACLE is Python, so it runs as an asyncio task on
the same loop — but the socket layer is still exercised end to end. The client
opens real UNIX connections to a live core.Server: core.sock (module role) and
events.sock (consumer role). No Ollama (observe-first; classify is a later
slice). Marked `integration`, deselected by default.

Verifies the dual-role client end to end: registers on core.sock, serves
oracle.status via the 4A router, consumes chaff.request.sent over events.sock
into the baseline, and emits oracle.baseline.updated after baseline_every events.
"""

import asyncio

import pytest
from core.broker import Event, EventBroker
from core.config import CoreConfig
from core.envelope import Response, parse
from core.lifecycle import Lifecycle
from core.registry import Registry
from core.server import Server
from core.tokens import TokenIssuer
from oracle.baseline import BaselineStore
from oracle.client import OracleClient

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


async def test_oracle_registers(tmp_path):
    server, registry, _ = _make_core(tmp_path)
    await server.start()
    store = BaselineStore(tmp_path / "baseline.db", tmp_path / "baseline.key")
    client = OracleClient(tmp_path, store)
    task = asyncio.create_task(client.run())
    try:
        assert await _wait(lambda: registry.is_registered("oracle"))
    finally:
        task.cancel()
        await server.stop()


async def test_oracle_status_roundtrip(tmp_path):
    server, registry, _ = _make_core(tmp_path)
    await server.start()
    store = BaselineStore(tmp_path / "baseline.db", tmp_path / "baseline.key")
    client = OracleClient(tmp_path, store)
    task = asyncio.create_task(client.run())
    try:
        assert await _wait(lambda: registry.is_registered("oracle"))
        resp = await _roundtrip(
            tmp_path / "core.sock",
            '{"jsonrpc":"2.0","id":1,"method":"oracle.status"}\n',
        )
        assert resp.error is None
        assert "baseline_events" in resp.result
    finally:
        task.cancel()
        await server.stop()


async def test_oracle_consumes_chaff_event(tmp_path):
    server, registry, broker = _make_core(tmp_path)
    await server.start()
    store = BaselineStore(tmp_path / "baseline.db", tmp_path / "baseline.key")
    client = OracleClient(tmp_path, store)
    task = asyncio.create_task(client.run())
    try:
        assert await _wait(lambda: registry.is_registered("oracle"))
        broker.publish(
            Event(
                topic="chaff.request.sent",
                payload={"url": "https://example", "gap_ms": 1000},
            )
        )
        assert await _wait(lambda: store.event_count() >= 1)
    finally:
        task.cancel()
        await server.stop()


async def test_oracle_emits_baseline_updated(tmp_path):
    server, registry, broker = _make_core(tmp_path)
    await server.start()
    store = BaselineStore(tmp_path / "baseline.db", tmp_path / "baseline.key")
    client = OracleClient(tmp_path, store, baseline_every=3)
    task = asyncio.create_task(client.run())
    sub = broker.subscribe(["oracle.baseline.updated"])
    try:
        assert await _wait(lambda: registry.is_registered("oracle"))
        for _ in range(3):
            broker.publish(Event(topic="chaff.request.sent", payload={}))
        ev = await asyncio.wait_for(sub.get(), timeout=5.0)
        assert ev.topic == "oracle.baseline.updated"
        assert ev.payload["event_count"] == 3
    finally:
        sub.close()
        task.cancel()
        await server.stop()
