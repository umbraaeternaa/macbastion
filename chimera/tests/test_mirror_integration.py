"""MIRROR daemon integration — mirror binary against a live core.

These spawn the compiled ./mirror and a real core.Server over UNIX sockets, so
they are marked `integration` and deselected by default (run with
`pytest -m integration`). No HTTP fixture: MIRROR makes no network calls.

RED note: these fail against the bootstrap skeleton binary (which prints a
version banner and exits, never registering); they go green once daemon wiring
lands (daemon.c + main.c rewrite + CHIMERA_SOCKET_DIR / MIRROR_CONFIG_PATH env).

Scope (honest, MANIFESTO §4): MIRROR registers and serves mirror.* via the 4A
router, but there is NO real event tap (GATED on code-signing + Accessibility
TCC) and NO event producer yet — so there is no event-subscription test here.
mirror.enable returns -31004 over the wire, like chaff's deferred profile.*.
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

MIRROR_DIR = Path(__file__).resolve().parent.parent / "modules" / "mirror"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def mirror_binary() -> Path:
    """Build ./mirror once; skip the whole module if the toolchain is unavailable."""
    result = subprocess.run(
        ["make", "-C", str(MIRROR_DIR)], capture_output=True, text=True
    )
    if result.returncode != 0:
        pytest.skip(f"mirror build failed:\n{result.stderr}")
    binary = MIRROR_DIR / "mirror"
    if not binary.exists():
        pytest.skip("mirror binary not produced")
    return binary


def _make_core(tmp_path: Path) -> tuple[Server, Registry]:
    config = CoreConfig.model_validate({"socket_dir": str(tmp_path)})
    broker = EventBroker()
    lifecycle = Lifecycle(config, broker)
    registry = Registry(lifecycle, broker)
    server = Server(config, registry, lifecycle, broker, TokenIssuer())
    return server, registry


def _write_config(tmp_path: Path) -> Path:
    """A minimal valid config (defaults — medium, no exclusions)."""
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"profile": "medium", "exclusions": []}))
    return path


def _spawn_mirror(binary: Path, socket_dir: Path, config_path: Path) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [str(binary)],
        env={
            "CHIMERA_SOCKET_DIR": str(socket_dir),
            "MIRROR_CONFIG_PATH": str(config_path),
            "PATH": "/usr/bin:/bin",
        },
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
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


# ---------------------------------------------------------------------------
# Tests — no network, no event tap
# ---------------------------------------------------------------------------


async def test_mirror_registers(mirror_binary: Path, tmp_path: Path) -> None:
    cfg = _write_config(tmp_path)
    server, registry = _make_core(tmp_path)
    await server.start()
    proc = _spawn_mirror(mirror_binary, tmp_path, cfg)
    try:
        assert await _wait_registered(registry, "mirror")
    finally:
        proc.terminate()
        await server.stop()


async def test_mirror_status_roundtrip(mirror_binary: Path, tmp_path: Path) -> None:
    cfg = _write_config(tmp_path)
    server, registry = _make_core(tmp_path)
    await server.start()
    proc = _spawn_mirror(mirror_binary, tmp_path, cfg)
    try:
        assert await _wait_registered(registry, "mirror")
        resp = await _roundtrip(
            tmp_path / "core.sock", '{"jsonrpc":"2.0","id":1,"method":"mirror.status"}\n'
        )
        assert resp.error is None
        assert resp.result["enabled"] is False
        assert resp.result["profile"] == "medium"
    finally:
        proc.terminate()
        await server.stop()


async def test_mirror_profile_set_roundtrip(mirror_binary: Path, tmp_path: Path) -> None:
    cfg = _write_config(tmp_path)
    server, registry = _make_core(tmp_path)
    await server.start()
    proc = _spawn_mirror(mirror_binary, tmp_path, cfg)
    try:
        assert await _wait_registered(registry, "mirror")
        resp = await _roundtrip(
            tmp_path / "core.sock",
            '{"jsonrpc":"2.0","id":2,"method":"mirror.profile.set","params":{"profile":"heavy"}}\n',
        )
        assert resp.error is None
        assert resp.result["profile"] == "heavy"
    finally:
        proc.terminate()
        await server.stop()


async def test_mirror_enable_deferred(mirror_binary: Path, tmp_path: Path) -> None:
    cfg = _write_config(tmp_path)
    server, registry = _make_core(tmp_path)
    await server.start()
    proc = _spawn_mirror(mirror_binary, tmp_path, cfg)
    try:
        assert await _wait_registered(registry, "mirror")
        resp = await _roundtrip(
            tmp_path / "core.sock", '{"jsonrpc":"2.0","id":3,"method":"mirror.enable"}\n'
        )
        assert resp.error is not None
        assert resp.error["code"] == -31004
    finally:
        proc.terminate()
        await server.stop()
