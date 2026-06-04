"""CHAFF daemon integration (Step 2D) — chaff binary against a live core.

These spawn the compiled ./chaff and a real core.Server over UNIX sockets, so
they are marked `integration` and deselected by default (run with
`pytest -m integration`). Hermetic: Tier 2 points chaff at a local HTTP server,
never the public internet.

RED note: these fail against the bootstrap binary (which exits immediately and
never registers); they go green once daemon wiring lands (http/ipc/daemon/main
+ CHIMERA_SOCKET_DIR / CHAFF_ENDPOINTS_PATH env support).
"""

import asyncio
import json
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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

pytestmark = pytest.mark.integration

CHAFF_DIR = Path(__file__).resolve().parent.parent / "modules" / "chaff"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def chaff_binary() -> Path:
    """Build ./chaff once; skip the whole module if the toolchain is unavailable."""
    result = subprocess.run(
        ["make", "-C", str(CHAFF_DIR)], capture_output=True, text=True
    )
    if result.returncode != 0:
        pytest.skip(f"chaff build failed:\n{result.stderr}")
    binary = CHAFF_DIR / "chaff"
    if not binary.exists():
        pytest.skip("chaff binary not produced")
    return binary


@pytest.fixture
def local_http() -> Any:
    """A loopback HTTP server recording GET paths (hermetic decoy target)."""
    hits: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 (http.server API)
            hits.append(self.path)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, *args: Any) -> None:
            pass  # silence

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        port = httpd.server_address[1]
        yield f"http://127.0.0.1:{port}/", hits
    finally:
        httpd.shutdown()
        thread.join(timeout=2.0)


def _make_core(tmp_path: Path) -> tuple[Server, Registry]:
    config = CoreConfig.model_validate({"socket_dir": str(tmp_path)})
    broker = EventBroker()
    lifecycle = Lifecycle(config, broker)
    registry = Registry(lifecycle, broker)
    server = Server(config, registry, lifecycle, broker, TokenIssuer())
    return server, registry


def _spawn_chaff(binary: Path, socket_dir: Path, endpoints_path: Path) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [str(binary)],
        env={
            "CHIMERA_SOCKET_DIR": str(socket_dir),
            "CHAFF_ENDPOINTS_PATH": str(endpoints_path),
            "PATH": "/usr/bin:/bin",
        },
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _write_local_endpoints(tmp_path: Path, base_url: str) -> Path:
    path = tmp_path / "endpoints.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "categories": ["dev"],
                "endpoints": [{"url": base_url, "category": "dev"}],
            }
        )
    )
    return path


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
# Tier 1 — no network
# ---------------------------------------------------------------------------


async def test_chaff_registers(chaff_binary: Path, tmp_path: Path, local_http: Any) -> None:
    base_url, _ = local_http
    eps = _write_local_endpoints(tmp_path, base_url)
    server, registry = _make_core(tmp_path)
    await server.start()
    proc = _spawn_chaff(chaff_binary, tmp_path, eps)
    try:
        assert await _wait_registered(registry, "chaff")
    finally:
        proc.terminate()
        await server.stop()


async def test_chaff_status_roundtrip(chaff_binary: Path, tmp_path: Path, local_http: Any) -> None:
    base_url, _ = local_http
    eps = _write_local_endpoints(tmp_path, base_url)
    server, registry = _make_core(tmp_path)
    await server.start()
    proc = _spawn_chaff(chaff_binary, tmp_path, eps)
    try:
        assert await _wait_registered(registry, "chaff")
        resp = await _roundtrip(
            tmp_path / "core.sock", '{"jsonrpc":"2.0","id":1,"method":"chaff.status"}\n'
        )
        assert resp.error is None
        assert "phase" in resp.result
    finally:
        proc.terminate()
        await server.stop()


async def test_chaff_profile_deferred(chaff_binary: Path, tmp_path: Path, local_http: Any) -> None:
    base_url, _ = local_http
    eps = _write_local_endpoints(tmp_path, base_url)
    server, registry = _make_core(tmp_path)
    await server.start()
    proc = _spawn_chaff(chaff_binary, tmp_path, eps)
    try:
        assert await _wait_registered(registry, "chaff")
        resp = await _roundtrip(
            tmp_path / "core.sock",
            '{"jsonrpc":"2.0","id":2,"method":"chaff.profile.start"}\n',
        )
        assert resp.error is not None
        assert resp.error["code"] == -31004
    finally:
        proc.terminate()
        await server.stop()


# ---------------------------------------------------------------------------
# Tier 2 — hermetic generation (local HTTP, no public internet)
# ---------------------------------------------------------------------------


async def test_chaff_generation_emits_event(
    chaff_binary: Path, tmp_path: Path, local_http: Any
) -> None:
    base_url, hits = local_http
    eps = _write_local_endpoints(tmp_path, base_url)
    server, registry = _make_core(tmp_path)
    await server.start()
    proc = _spawn_chaff(chaff_binary, tmp_path, eps)
    ev_reader = ev_writer = None
    try:
        assert await _wait_registered(registry, "chaff")
        # subscribe to chaff.request.sent on events.sock
        ev_reader, ev_writer = await asyncio.open_unix_connection(str(tmp_path / "events.sock"))
        ev_writer.write(
            b'{"jsonrpc":"2.0","id":1,"method":"core.subscribe",'
            b'"params":{"topics":["chaff.request.sent"]}}\n'
        )
        await ev_writer.drain()
        await asyncio.wait_for(ev_reader.readline(), timeout=5.0)  # sub ack
        # start generation
        await _roundtrip(
            tmp_path / "core.sock",
            '{"jsonrpc":"2.0","id":3,"method":"chaff.generation.start"}\n',
        )
        pushed = await asyncio.wait_for(ev_reader.readline(), timeout=10.0)
        note = parse(pushed.decode())
        assert note.method == "chaff.request.sent"
        assert len(hits) >= 1  # chaff actually GET the local endpoint
    finally:
        if ev_writer is not None:
            ev_writer.close()
        proc.terminate()
        await server.stop()
