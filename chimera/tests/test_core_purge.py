"""core.purge operator command -> Tier-0 executor (PURGE T0-b): broadcast purge.imminent +
run_tier0 (evict CHIMERA Keychain via the shim + wipe state DBs). Default-suite units — a
recording ShimClient subclass (never touches a socket) + a temp state_dir. RED until
core.purge is handled."""

import asyncio

from core.broker import EventBroker
from core.config import CoreConfig
from core.envelope import Request
from core.errors import ChimeraError
from core.lifecycle import Lifecycle
from core.registry import Registry
from core.server import Server
from core.shim_client import ShimClient
from core.tokens import TokenIssuer


class _RecordingShim(ShimClient):
    """A ShimClient whose evict() records the call instead of touching the real Keychain."""

    def __init__(self) -> None:
        super().__init__("/nonexistent-chimera-test.sock")
        self.evict_calls = 0

    async def evict(self) -> dict[str, object]:
        self.evict_calls += 1
        return {"ok": True, "noop": False}


def _server(tmp_path, state_dir, shim_client=None):
    config = CoreConfig.model_validate(
        {"socket_dir": str(tmp_path), "state_dir": str(state_dir)}
    )
    broker = EventBroker()
    lifecycle = Lifecycle(config, broker)
    registry = Registry(lifecycle, broker)
    server = Server(config, registry, lifecycle, broker, TokenIssuer(), shim_client=shim_client)
    return server, broker


def _purge_req():
    return Request(jsonrpc="2.0", id=1, method="core.purge", params=None)


async def test_core_purge_without_shim_precondition(tmp_path):
    state = tmp_path / "state"
    state.mkdir()
    server, _ = _server(tmp_path, state, shim_client=None)
    conn = server.new_connection()
    resp = await server.handle_command(_purge_req(), conn)
    assert resp.error is not None
    assert resp.error["code"] == ChimeraError.PRECONDITION_FAILED


async def test_core_purge_runs_tier0(tmp_path):
    state = tmp_path / "state"
    state.mkdir()
    (state / "oracle_baseline.json").write_text("x")
    (state / "pulse_history.db").write_text("y")
    shim = _RecordingShim()
    server, _ = _server(tmp_path, state, shim_client=shim)
    conn = server.new_connection()
    resp = await server.handle_command(_purge_req(), conn)
    assert resp.error is None
    assert resp.result is not None
    assert resp.result["keychain_evicted"] is True
    assert resp.result["state_files_removed"] == 2
    assert shim.evict_calls == 1
    assert not (state / "oracle_baseline.json").exists()
    assert not (state / "pulse_history.db").exists()


async def test_core_purge_broadcasts_imminent(tmp_path):
    state = tmp_path / "state"
    state.mkdir()
    server, broker = _server(tmp_path, state, shim_client=_RecordingShim())
    sub = broker.subscribe(["purge.imminent"])
    conn = server.new_connection()
    await server.handle_command(_purge_req(), conn)
    ev = await asyncio.wait_for(sub.get(), 1.0)
    assert ev.topic == "purge.imminent"
