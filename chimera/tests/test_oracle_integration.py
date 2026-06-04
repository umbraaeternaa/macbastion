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
from oracle.detector import Detector
from oracle.llm import LlmClient

pytestmark = pytest.mark.integration


class FakeDetector:
    """Hermetic detector injected into the client (no Ollama)."""

    async def classify(self, event):
        return {"score": 0.42, "reasoning": "hermetic"}

    def get_threshold(self):
        return 0.7

    def set_threshold(self, value):
        return {"threshold": value}


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


# -- Mode B (MD-B slice) ----------------------------------------------------


async def test_oracle_classify_via_4a(tmp_path):
    server, registry, _ = _make_core(tmp_path)
    await server.start()
    store = BaselineStore(tmp_path / "baseline.db", tmp_path / "baseline.key")
    client = OracleClient(tmp_path, store, detector=FakeDetector())
    task = asyncio.create_task(client.run())
    try:
        assert await _wait(lambda: registry.is_registered("oracle"))
        resp = await _roundtrip(
            tmp_path / "core.sock",
            '{"jsonrpc":"2.0","id":1,"method":"oracle.classify",'
            '"params":{"event":{"source":"chaff","type":"request.sent"}}}\n',
        )
        assert resp.error is None
        assert "score" in resp.result
        assert "reasoning" in resp.result
    finally:
        task.cancel()
        await server.stop()


async def test_oracle_threshold_set_via_4a(tmp_path):
    server, registry, _ = _make_core(tmp_path)
    await server.start()
    store = BaselineStore(tmp_path / "baseline.db", tmp_path / "baseline.key")
    client = OracleClient(tmp_path, store, detector=FakeDetector())
    task = asyncio.create_task(client.run())
    try:
        assert await _wait(lambda: registry.is_registered("oracle"))
        resp = await _roundtrip(
            tmp_path / "core.sock",
            '{"jsonrpc":"2.0","id":2,"method":"oracle.threshold.set",'
            '"params":{"threshold":0.5}}\n',
        )
        assert resp.error is None
        assert resp.result["threshold"] == 0.5
    finally:
        task.cancel()
        await server.stop()


async def test_oracle_status_reports_model_and_classifications(tmp_path):
    server, registry, _ = _make_core(tmp_path)
    await server.start()
    store = BaselineStore(tmp_path / "baseline.db", tmp_path / "baseline.key")
    client = OracleClient(tmp_path, store, detector=FakeDetector())
    task = asyncio.create_task(client.run())
    try:
        assert await _wait(lambda: registry.is_registered("oracle"))
        resp = await _roundtrip(
            tmp_path / "core.sock",
            '{"jsonrpc":"2.0","id":3,"method":"oracle.status"}\n',
        )
        assert resp.error is None
        assert "model" in resp.result
        assert "classifications_today" in resp.result  # added by Mode B slice
    finally:
        task.cancel()
        await server.stop()


@pytest.mark.ollama
async def test_classify_real_ollama(tmp_path):
    """Opt-in (-m ollama): hit the real llama3.2:1b. Structural asserts only."""
    llm = LlmClient()
    if not llm.available():
        pytest.skip("Ollama not reachable on localhost:11434")
    store = BaselineStore(tmp_path / "baseline.db", tmp_path / "baseline.key")
    det = Detector(llm, store)
    result = await det.classify(
        {"source": "chaff", "type": "request.sent", "payload": {"url": "https://x"}}
    )
    assert 0.0 <= result["score"] <= 1.0
    assert isinstance(result["reasoning"], str) and result["reasoning"]


@pytest.mark.ollama
async def test_classify_real_ollama_explainable(tmp_path):
    """Opt-in (-m ollama): explainability fields from a real llama3.2:1b.

    Structural asserts only (LLM text is non-deterministic).
    """
    llm = LlmClient()
    if not llm.available():
        pytest.skip("Ollama not reachable on localhost:11434")
    store = BaselineStore(tmp_path / "baseline.db", tmp_path / "baseline.key")
    store.record_event(
        ts="2026-06-04T14:00:00+00:00", source="chaff",
        event_type="request.sent", payload={"url": "https://x"},
    )
    det = Detector(llm, store)
    result = await det.classify(
        {"source": "chaff", "type": "request.sent", "ts": "2026-06-04T03:14:00+00:00"}
    )
    assert 0.0 <= result["score"] <= 1.0
    assert isinstance(result["reasoning"], str) and result["reasoning"]
    assert isinstance(result["context_factors"], list)
    assert all(isinstance(x, str) for x in result["context_factors"])
    assert isinstance(result["similar_events"], list)
