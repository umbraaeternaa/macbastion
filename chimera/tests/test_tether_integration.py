"""TETHER daemon integration — the ./tether C++ binary against a live core.

Spawns the compiled ./tether and a real core.Server over UNIX sockets; marked
`integration` (deselected by default; run with `pytest -m integration`). No
network: TETHER is Bluetooth-only.

RED note: these fail against the daemon-wiring RED skeleton — main connects but
daemon_run is stubbed (returns immediately, never sending core.register), so the
module never registers. They go green once daemon_run wires register + the
poll/tick/heartbeat/serve loop.

Honest scope (MANIFESTO §4): the production RSSI source is CoreBluetooth, GATED
on Bluetooth HW + TCC, so a plain spawn emits NO presence. The emit test sets
TETHER_SYNTHETIC_RSSI (a scripted source — tests/dev ONLY; production never sets
it) to drive a present→absent sequence and observe the relayed tether.absent.
Escalation timing is covered hermetically in the Monitor Unity suite (FakeClock),
not dragged through real 30s grace here.
"""

import asyncio
import json
import subprocess
from pathlib import Path

import pytest
from core.broker import EventBroker
from core.config import CoreConfig
from core.envelope import Response, parse
from core.lifecycle import Lifecycle
from core.registry import Registry
from core.server import Server
from core.tokens import TokenIssuer

pytestmark = pytest.mark.integration

TETHER_DIR = Path(__file__).resolve().parent.parent / "modules" / "tether"


@pytest.fixture(scope="session")
def tether_binary() -> Path:
    """Build ./tether once; skip the module if the C++ toolchain is unavailable."""
    result = subprocess.run(["make", "-C", str(TETHER_DIR)], capture_output=True, text=True)
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


def _write_config(tmp_path: Path, **extra: object) -> Path:
    path = tmp_path / "tether.json"
    path.write_text(json.dumps({"tick_ms": 20, **extra}))
    return path


def _write_synthetic(tmp_path: Path, samples: list[dict]) -> Path:
    path = tmp_path / "rssi.json"
    path.write_text(json.dumps({"samples": samples}))
    return path


def _spawn_tether(
    binary: Path, socket_dir: Path, config_path: Path, synthetic: Path | None = None
) -> subprocess.Popen[bytes]:
    env = {
        "CHIMERA_SOCKET_DIR": str(socket_dir),
        "TETHER_CONFIG_PATH": str(config_path),
        "PATH": "/usr/bin:/bin",
    }
    if synthetic is not None:
        env["TETHER_SYNTHETIC_RSSI"] = str(synthetic)
    return subprocess.Popen(
        [str(binary)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


async def _wait_registered(registry: Registry, name: str, timeout_s: float = 5.0) -> bool:
    for _ in range(int(timeout_s / 0.05)):
        if registry.is_registered(name):
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


async def test_tether_registers(tether_binary: Path, tmp_path: Path) -> None:
    cfg = _write_config(tmp_path)
    server, registry, _ = _make_core(tmp_path)
    await server.start()
    proc = _spawn_tether(tether_binary, tmp_path, cfg)
    try:
        assert await _wait_registered(registry, "tether")
    finally:
        proc.terminate()
        await server.stop()


async def test_tether_status_roundtrip(tether_binary: Path, tmp_path: Path) -> None:
    cfg = _write_config(tmp_path)
    server, registry, _ = _make_core(tmp_path)
    await server.start()
    proc = _spawn_tether(tether_binary, tmp_path, cfg)
    try:
        assert await _wait_registered(registry, "tether")
        resp = await _roundtrip(
            tmp_path / "core.sock", '{"jsonrpc":"2.0","id":1,"method":"tether.status"}\n'
        )
        assert resp.error is None
        assert resp.result["l3_armed"] is False
        assert resp.result["companion_paired"] is False
    finally:
        proc.terminate()
        await server.stop()


async def test_tether_config_set_roundtrip(tether_binary: Path, tmp_path: Path) -> None:
    cfg = _write_config(tmp_path)
    server, registry, _ = _make_core(tmp_path)
    await server.start()
    proc = _spawn_tether(tether_binary, tmp_path, cfg)
    try:
        assert await _wait_registered(registry, "tether")
        resp = await _roundtrip(
            tmp_path / "core.sock",
            '{"jsonrpc":"2.0","id":2,"method":"tether.config.set",'
            '"params":{"near_threshold":-65}}\n',
        )
        assert resp.error is None
        assert resp.result["config"]["near_threshold"] == -65
    finally:
        proc.terminate()
        await server.stop()


async def test_tether_pair_deferred(tether_binary: Path, tmp_path: Path) -> None:
    cfg = _write_config(tmp_path)
    server, registry, _ = _make_core(tmp_path)
    await server.start()
    proc = _spawn_tether(tether_binary, tmp_path, cfg)
    try:
        assert await _wait_registered(registry, "tether")
        resp = await _roundtrip(
            tmp_path / "core.sock", '{"jsonrpc":"2.0","id":3,"method":"tether.pair.start"}\n'
        )
        assert resp.error is not None
        assert resp.error["code"] == -31004
    finally:
        proc.terminate()
        await server.stop()


async def test_tether_emits_absent(tether_binary: Path, tmp_path: Path) -> None:
    """Synthetic source drives present→absent; observe the relayed tether.absent."""
    cfg = _write_config(tmp_path)
    samples = [{"rssi": -50, "seen": True, "clean": False}] * 2 + [
        {"rssi": 0, "seen": False, "clean": False}
    ] * 6
    synth = _write_synthetic(tmp_path, samples)
    server, registry, broker = _make_core(tmp_path)
    await server.start()
    sub = broker.subscribe(["tether.absent"])
    proc = _spawn_tether(tether_binary, tmp_path, cfg, synthetic=synth)
    try:
        assert await _wait_registered(registry, "tether")
        ev = await asyncio.wait_for(sub.get(), timeout=5.0)
        assert ev.topic == "tether.absent"
        assert "disappearance_class" in ev.payload
    finally:
        sub.close()
        proc.terminate()
        await server.stop()
