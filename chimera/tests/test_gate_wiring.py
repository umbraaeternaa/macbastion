"""Cognitive gate live-wiring tests (GW-1…GW-6).

Two layers:
- unit (default): _gate / _refresh_danger on a bare Server (no sockets) — the enforcement
  decision and the danger-set caching, with asyncio.sleep / _dispatch_internal stubbed.
- integration (marked): a live core.Server — a pulse.mode.changed event updates the cached
  mode, and a registering PULSE refreshes the danger set over the real socket.

GREEN — _gate / _refresh_danger are implemented and the wiring (mode subscription,
refresh-on-register, the _route hook) is in place; the assertions are unchanged from RED.
"""

import asyncio

import pytest
from core.broker import Event, EventBroker
from core.config import CoreConfig
from core.envelope import Response
from core.errors import ChimeraError, RpcError
from core.lifecycle import Lifecycle
from core.override import OverrideStore
from core.registry import Registry
from core.server import Server
from core.tokens import TokenIssuer
from pulse.baseline import BaselineStore
from pulse.client import PulseClient
from pulse.registry import DangerRegistry


def _bare_server(tmp_path):
    config = CoreConfig.model_validate({"socket_dir": str(tmp_path)})
    broker = EventBroker()
    lifecycle = Lifecycle(config, broker)
    registry = Registry(lifecycle, broker)
    return Server(config, registry, lifecycle, broker, TokenIssuer())


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


# -- unit: _gate enforcement ------------------------------------------------


async def test_gate_blocks_at_exhausted(tmp_path):
    server = _bare_server(tmp_path)
    server._danger_set = {"worker.act"}
    server._pulse_mode = "exhausted"
    with pytest.raises(RpcError) as ei:
        await server._gate("worker.act", None)
    assert ei.value.code == ChimeraError.DENIED_BY_POLICY


async def test_gate_delays_at_tired(tmp_path, monkeypatch):
    server = _bare_server(tmp_path)
    server._danger_set = {"worker.act"}
    server._pulse_mode = "tired"
    slept: list[float] = []

    async def fake_sleep(seconds):
        slept.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    await server._gate("worker.act", None)  # delays, does not raise
    assert slept == [5.0]


async def test_gate_allows_non_danger(tmp_path, monkeypatch):
    server = _bare_server(tmp_path)
    server._danger_set = {"worker.act"}
    server._pulse_mode = "exhausted"
    slept: list[float] = []

    async def fake_sleep(seconds):
        slept.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    await server._gate("safe.method", None)  # not in danger set -> no-op, no raise
    assert slept == []


async def test_gate_allows_danger_at_normal(tmp_path, monkeypatch):
    server = _bare_server(tmp_path)
    server._danger_set = {"worker.act"}
    server._pulse_mode = "normal"
    slept: list[float] = []

    async def fake_sleep(seconds):
        slept.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    await server._gate("worker.act", None)  # normal -> allow, no delay, no raise
    assert slept == []


async def test_gate_override_allows_at_exhausted(tmp_path):
    server = _bare_server(tmp_path)
    server._override_store = OverrideStore(tmp_path / "override.json")
    server._override_store.set_phrase("let me in")
    server._danger_set = {"worker.act"}
    server._pulse_mode = "exhausted"
    await server._gate("worker.act", {"_override": "let me in"})  # correct -> allowed


async def test_gate_blocks_exhausted_wrong_override(tmp_path):
    server = _bare_server(tmp_path)
    server._override_store = OverrideStore(tmp_path / "override.json")
    server._override_store.set_phrase("let me in")
    server._danger_set = {"worker.act"}
    server._pulse_mode = "exhausted"
    with pytest.raises(RpcError) as ei:
        await server._gate("worker.act", {"_override": "wrong"})
    assert ei.value.code == ChimeraError.DENIED_BY_POLICY


def test_strip_override_removes_secret(tmp_path):
    server = _bare_server(tmp_path)
    assert server._strip_override({"_override": "secret", "url": "x"}) == {"url": "x"}
    assert server._strip_override({"a": 1}) == {"a": 1}  # untouched when absent


async def test_refresh_danger_caches_registry(tmp_path, monkeypatch):
    server = _bare_server(tmp_path)

    async def fake_dispatch(method, params):
        assert method == "pulse.danger.list"
        return Response(jsonrpc="2.0", id=1, result={"registry": ["a", "b"]})

    monkeypatch.setattr(server, "_dispatch_internal", fake_dispatch)
    await server._refresh_danger()
    assert server._danger_set == {"a", "b"}


# -- integration: live sourcing ---------------------------------------------


@pytest.mark.integration
async def test_mode_changed_updates_mode(tmp_path):
    server, _, broker = _make_core(tmp_path)
    await server.start()
    try:
        broker.publish(
            Event(topic="pulse.mode.changed", payload={"new_mode": "caution"})
        )
        assert await _wait(lambda: server._pulse_mode == "caution")
    finally:
        await server.stop()


@pytest.mark.integration
async def test_pulse_register_triggers_refresh(tmp_path):
    server, registry, _ = _make_core(tmp_path)
    await server.start()
    store = BaselineStore(tmp_path / "baseline.db", tmp_path / "baseline.key")
    danger = DangerRegistry(tmp_path / "registry.json")
    danger.add("worker.act")
    client = PulseClient(
        tmp_path, store, danger_registry=danger, session_start="2026-06-12T14:00:00"
    )
    task = asyncio.create_task(client.run())
    try:
        assert await _wait(lambda: registry.is_registered("pulse"))
        assert await _wait(lambda: "worker.act" in server._danger_set)
    finally:
        task.cancel()
        await server.stop()
