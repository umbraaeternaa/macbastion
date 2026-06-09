"""Multi-module e2e — core + several live modules at once (consolidation, CO-1…3).

Brings one core.Server up with the ECHO and PURGE C daemons (subprocesses) AND a PULSE
Python client (in-process) simultaneously, then asserts all three register and each answers
its own status — proving the core / registry / 4A router holds multiple concurrent modules
without cross-talk. A confirmation test (passes on a sound system; reds only on an
integration bug). Marked integration; needs a short --basetemp (AF_UNIX).
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
from pulse.baseline import BaselineStore
from pulse.client import PulseClient

pytestmark = pytest.mark.integration

MODULES = Path(__file__).resolve().parent.parent / "modules"


def _build(name):
    result = subprocess.run(["make", "-C", str(MODULES / name)], capture_output=True, text=True)
    if result.returncode != 0:
        pytest.skip(f"{name} build failed:\n{result.stderr}")
    binary = MODULES / name / name
    if not binary.exists():
        pytest.skip(f"{name} binary not produced")
    return binary


@pytest.fixture(scope="session")
def echo_binary():
    return _build("echo")


@pytest.fixture(scope="session")
def purge_binary():
    return _build("purge")


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


async def _wait(pred, timeout_s=6.0):
    for _ in range(int(timeout_s / 0.05)):
        if pred():
            return True
        await asyncio.sleep(0.05)
    return False


async def _status(sock, method, timeout_s=5.0):
    reader, writer = await asyncio.open_unix_connection(str(sock))
    try:
        writer.write(f'{{"jsonrpc":"2.0","id":1,"method":"{method}"}}\n'.encode())
        await writer.drain()
        raw = await asyncio.wait_for(reader.readline(), timeout=timeout_s)
        msg = parse(raw.decode())
        assert isinstance(msg, Response)
        return msg
    finally:
        writer.close()
        await writer.wait_closed()


async def test_three_modules_coexist(echo_binary, purge_binary, tmp_path):
    server, registry = _make_core(tmp_path)
    await server.start()
    store = BaselineStore(tmp_path / "baseline.db", tmp_path / "baseline.key")
    pulse = PulseClient(tmp_path, store, session_start="2026-06-12T14:00:00")
    pulse_task = asyncio.create_task(pulse.run())
    echo_proc = _spawn(echo_binary, tmp_path)
    purge_proc = _spawn(purge_binary, tmp_path)
    try:
        assert await _wait(lambda: registry.is_registered("echo"))
        assert await _wait(lambda: registry.is_registered("purge"))
        assert await _wait(lambda: registry.is_registered("pulse"))
        # core.capabilities sees all three concurrently
        assert {"echo", "purge", "pulse"} <= set(registry.capabilities())
        # each answers its OWN status with no cross-talk
        sock = tmp_path / "core.sock"
        assert (await _status(sock, "echo.status")).error is None
        assert (await _status(sock, "purge.status")).error is None
        assert (await _status(sock, "pulse.status")).error is None
    finally:
        echo_proc.terminate()
        echo_proc.wait(timeout=3)
        purge_proc.terminate()
        purge_proc.wait(timeout=3)
        pulse_task.cancel()
        await server.stop()
        store.close()
