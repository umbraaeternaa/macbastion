"""ECHO daemon integration — the compiled echo binary against a live core.

Spawns ./echo + a real core.Server over UNIX sockets (marked integration, deselected by
default; needs a short --basetemp for AF_UNIX). RED: fails against the bootstrap binary
(exits immediately, never registers); green once the socket loop (ipc/daemon/main) lands.
"""

import asyncio
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

ECHO_DIR = Path(__file__).resolve().parent.parent / "modules" / "echo"


@pytest.fixture(scope="session")
def echo_binary():
    result = subprocess.run(["make", "-C", str(ECHO_DIR)], capture_output=True, text=True)
    if result.returncode != 0:
        pytest.skip(f"echo build failed:\n{result.stderr}")
    binary = ECHO_DIR / "echo"
    if not binary.exists():
        pytest.skip("echo binary not produced")
    return binary


def _make_core(tmp_path):
    config = CoreConfig.model_validate({"socket_dir": str(tmp_path)})
    broker = EventBroker()
    lifecycle = Lifecycle(config, broker)
    registry = Registry(lifecycle, broker)
    server = Server(config, registry, lifecycle, broker, TokenIssuer())
    return server, registry


def _spawn(binary, socket_dir):
    return subprocess.Popen(
        [str(binary)],
        env={"CHIMERA_SOCKET_DIR": str(socket_dir), "PATH": "/usr/bin:/bin"},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


async def _wait_registered(registry, name, timeout_s=5.0):
    for _ in range(int(timeout_s / 0.05)):
        if registry.is_registered(name):
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


async def test_echo_registers(echo_binary, tmp_path):
    server, registry = _make_core(tmp_path)
    await server.start()
    proc = _spawn(echo_binary, tmp_path)
    try:
        assert await _wait_registered(registry, "echo")
    finally:
        proc.terminate()
        proc.wait(timeout=3)
        await server.stop()


async def test_echo_status_roundtrip(echo_binary, tmp_path):
    server, registry = _make_core(tmp_path)
    await server.start()
    proc = _spawn(echo_binary, tmp_path)
    try:
        assert await _wait_registered(registry, "echo")
        resp = await _roundtrip(
            tmp_path / "core.sock", '{"jsonrpc":"2.0","id":1,"method":"echo.status"}\n'
        )
        assert resp.error is None
        assert resp.result["target_kbps"] == 100
    finally:
        proc.terminate()
        proc.wait(timeout=3)
        await server.stop()
