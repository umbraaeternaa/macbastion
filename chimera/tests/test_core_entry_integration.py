"""Core entry-point integration (SV-1) — the wired core actually serves, and the
`python -m core` process serves + exits cleanly on SIGTERM. Marked integration (real
sockets / subprocess); needs a short --basetemp (AF_UNIX). RED until the entry lands.

core.__main__ is imported inside the tests so the RED stub fails the test rather than
aborting collection.
"""

import asyncio
import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest
from core.config import CoreConfig
from core.envelope import Response, parse

pytestmark = pytest.mark.integration

CHIMERA = Path(__file__).resolve().parent.parent

_REGISTER = (
    b'{"jsonrpc":"2.0","id":1,"method":"core.register","params":'
    b'{"module":"probe","version":"0","methods":[],"events":[],"depends_on":[]}}\n'
)


async def _register_roundtrip(sock):
    reader, writer = await asyncio.open_unix_connection(str(sock))
    try:
        writer.write(_REGISTER)
        await writer.drain()
        raw = await asyncio.wait_for(reader.readline(), timeout=5.0)
        return parse(raw.decode())
    finally:
        writer.close()
        await writer.wait_closed()


async def test_build_core_serves(tmp_path):
    from core.__main__ import build_core

    server = build_core(CoreConfig.model_validate({"socket_dir": str(tmp_path)}))
    await server.start()
    try:
        msg = await _register_roundtrip(tmp_path / "core.sock")
        assert isinstance(msg, Response)
        assert msg.error is None
    finally:
        await server.stop()


async def test_main_subprocess_serves_and_stops(tmp_path):
    proc = subprocess.Popen(
        [sys.executable, "-m", "core"],
        cwd=str(CHIMERA),
        env={**os.environ, "CHIMERA_SOCKET_DIR": str(tmp_path)},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        sock = tmp_path / "core.sock"
        for _ in range(100):
            if sock.exists():
                break
            await asyncio.sleep(0.05)
        assert sock.exists(), "core.sock never appeared"
        msg = await _register_roundtrip(sock)
        assert isinstance(msg, Response)
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)
    assert proc.returncode is not None  # the process exited on SIGTERM
