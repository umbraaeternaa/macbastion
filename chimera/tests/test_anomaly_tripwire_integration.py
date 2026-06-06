"""e2e: the Anomaly-Tripwire chain (idea #3) — ORACLE -> core -> TETHER.

CONFIRMATION test, NOT RED->GREEN: all three links are already done and proven
separately — 3A (TETHER tether.heighten + Monitor sync, Unity), 3B (core relay,
server unit), 3C (ORACLE emit-on-classify, client unit). This proves they are
actually WIRED over real sockets end to end, so it is expected to pass on write.

Chain (every link real-socket; the only seam is the score, faked to skip Ollama):
  oracle.classify (high-score FakeDetector)
    -> ORACLE emits oracle.anomaly.detected on core.sock
      -> core publishes it to the broker
        -> the relay (3B, RELAY_RULES) issues tether.heighten on core's authority
          -> the TETHER binary sets rt.heightened + Monitor.set_heightened
  observable proof: tether.status flips heightened false -> true.

FULL spin: core + ORACLE in-process (asyncio tasks) + the TETHER C++ binary as a
subprocess — the same fragility level as test_tether_integration (one subprocess).

Honest scope (3D-7): this proves the WIRE, not autonomy — the emit is still
operator-triggered (3C MVP); auto-classify-per-event is a later tail. Ollama is not
in the loop (faked score). TETHER's L1/L2/L3 effects remain gated (heighten only
changes sensitivity — EMIT-ONLY).
"""

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from core.broker import EventBroker
from core.config import CoreConfig
from core.envelope import Response, parse
from core.lifecycle import Lifecycle
from core.registry import Registry
from core.server import Server
from core.tokens import TokenIssuer
from oracle.baseline import BaselineStore
from oracle.client import OracleClient

pytestmark = pytest.mark.integration

TETHER_DIR = Path(__file__).resolve().parent.parent / "modules" / "tether"


class FakeDetector:
    """Detector stand-in with a fixed score (no Ollama). High score (>= threshold)
    drives the emit; low score stays below the gate."""

    def __init__(self, score: float, threshold: float = 0.7) -> None:
        self._score = score
        self._threshold = threshold

    async def classify(self, event: dict[str, Any]) -> dict[str, Any]:
        return {
            "score": self._score,
            "reasoning": "suspicious" if self._score >= self._threshold else "normal",
            "context_factors": [],
            "similar_events": [],
        }

    def get_threshold(self) -> float:
        return self._threshold

    def set_threshold(self, value: float) -> dict[str, Any]:
        return {"threshold": value}


@pytest.fixture(scope="session")
def tether_binary() -> Path:
    """Build ./tether once; skip the module if the C++ toolchain is unavailable."""
    result = subprocess.run(
        ["make", "-C", str(TETHER_DIR)], capture_output=True, text=True
    )
    if result.returncode != 0:
        pytest.skip(f"tether build failed:\n{result.stderr}")
    binary = TETHER_DIR / "tether"
    if not binary.exists():
        pytest.skip("tether binary not produced")
    return binary


def _make_core(tmp_path: Path) -> tuple[Server, Registry, EventBroker]:
    config = CoreConfig.model_validate({"socket_dir": str(tmp_path)})
    broker = EventBroker()
    lifecycle = Lifecycle(config, broker)
    registry = Registry(lifecycle, broker)
    server = Server(config, registry, lifecycle, broker, TokenIssuer())
    return server, registry, broker


def _spawn_tether(binary: Path, socket_dir: Path, config_path: Path) -> subprocess.Popen[bytes]:
    env = {
        "CHIMERA_SOCKET_DIR": str(socket_dir),
        "TETHER_CONFIG_PATH": str(config_path),
        "PATH": "/usr/bin:/bin",
    }
    return subprocess.Popen(
        [str(binary)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


def _write_tether_config(tmp_path: Path) -> Path:
    path = tmp_path / "tether.json"
    path.write_text(json.dumps({"tick_ms": 20}))
    return path


async def _wait(pred: Any, timeout_s: float = 5.0) -> bool:
    for _ in range(int(timeout_s / 0.05)):
        if pred():
            return True
        await asyncio.sleep(0.05)
    return False


async def _roundtrip(sock: Path, line: str, timeout_s: float = 5.0) -> Response:
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


async def _status(sock: Path) -> dict[str, Any]:
    resp = await _roundtrip(
        sock, '{"jsonrpc":"2.0","id":9,"method":"tether.status"}\n'
    )
    assert resp.error is None
    return resp.result


_HIGH_CLASSIFY = (
    '{"jsonrpc":"2.0","id":1,"method":"oracle.classify",'
    '"params":{"event":{"source":"chaff","type":"request.sent"}}}\n'
)


async def _spin(tmp_path: Path, tether_binary: Path, score: float):
    """Start core + ORACLE (FakeDetector(score)) + the TETHER binary; wait both
    registered. Returns (server, registry, oracle_task, proc) for teardown."""
    cfg = _write_tether_config(tmp_path)
    server, registry, _ = _make_core(tmp_path)
    await server.start()
    store = BaselineStore(tmp_path / "baseline.db", tmp_path / "baseline.key")
    oracle = OracleClient(tmp_path, store, detector=FakeDetector(score))
    oracle_task = asyncio.create_task(oracle.run())
    proc = _spawn_tether(tether_binary, tmp_path, cfg)
    assert await _wait(lambda: registry.is_registered("oracle"))
    assert await _wait(lambda: registry.is_registered("tether"))
    return server, registry, oracle_task, proc


async def test_anomaly_triggers_tether_heighten(
    tether_binary: Path, tmp_path: Path
) -> None:
    """High-score classify -> anomaly -> relay -> tether.heighten (full wire)."""
    server, _registry, oracle_task, proc = await _spin(tmp_path, tether_binary, 0.95)
    core_sock = tmp_path / "core.sock"
    try:
        # Baseline: TETHER not heightened yet.
        assert (await _status(core_sock))["heightened"] is False

        # Fire a high-score classify; ORACLE emits oracle.anomaly.detected, which
        # the core relay turns into tether.heighten (all real-socket).
        resp = await _roundtrip(core_sock, _HIGH_CLASSIFY)
        assert resp.error is None
        assert resp.result["score"] == 0.95

        # The chain is async (emit -> broker -> relay -> tether); poll briefly.
        async def _heightened() -> bool:
            return (await _status(core_sock)).get("heightened") is True

        flipped = False
        for _ in range(100):  # ~5s max, deterministic short steps
            if await _heightened():
                flipped = True
                break
            await asyncio.sleep(0.05)
        assert flipped, "tether.heighten never reached TETHER via the relay chain"
    finally:
        proc.terminate()
        oracle_task.cancel()
        await server.stop()


async def test_no_anomaly_keeps_tether_baseline(
    tether_binary: Path, tmp_path: Path
) -> None:
    """Low-score classify stays below threshold -> no anomaly -> TETHER unchanged."""
    server, _registry, oracle_task, proc = await _spin(tmp_path, tether_binary, 0.1)
    core_sock = tmp_path / "core.sock"
    try:
        assert (await _status(core_sock))["heightened"] is False

        resp = await _roundtrip(core_sock, _HIGH_CLASSIFY)  # low-score detector
        assert resp.error is None
        assert resp.result["score"] == 0.1

        # Give any (non-)relay a chance to settle, then confirm no heighten fired.
        await asyncio.sleep(0.5)
        assert (await _status(core_sock))["heightened"] is False
    finally:
        proc.terminate()
        oracle_task.cancel()
        await server.stop()
