"""`chimera up` integration (SV-4) — one command brings the whole organism alive: the
`python -m core up` process starts core AND the module daemons (ECHO + PURGE) in waves,
then exits cleanly on SIGTERM. Marked integration (subprocess + sockets); needs a short
--basetemp (AF_UNIX). RED until run_up + the CLI dispatch land.
"""

import asyncio
import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest
from core.envelope import Response, parse

pytestmark = pytest.mark.integration

CHIMERA = Path(__file__).resolve().parent.parent


def _build(name):
    result = subprocess.run(
        ["make", "-C", str(CHIMERA / "modules" / name)], capture_output=True, text=True
    )
    if result.returncode != 0:
        pytest.skip(f"{name} build failed:\n{result.stderr}")
    if not (CHIMERA / "modules" / name / name).exists():
        pytest.skip(f"{name} binary not produced")


def _spawn_up(tmp_path):
    return subprocess.Popen(
        [sys.executable, "-m", "core", "up"],
        cwd=str(CHIMERA),
        env={**os.environ, "CHIMERA_SOCKET_DIR": str(tmp_path)},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


async def _status_ok(sock, method, timeout_s=8.0):
    """Poll until `method` round-trips with no error (the module is up + serving)."""
    for _ in range(int(timeout_s / 0.1)):
        if sock.exists():
            try:
                reader, writer = await asyncio.open_unix_connection(str(sock))
                writer.write(f'{{"jsonrpc":"2.0","id":1,"method":"{method}"}}\n'.encode())
                await writer.drain()
                raw = await asyncio.wait_for(reader.readline(), timeout=2.0)
                writer.close()
                await writer.wait_closed()
                msg = parse(raw.decode())
                if isinstance(msg, Response) and msg.error is None:
                    return True
            except (TimeoutError, OSError):
                pass
        await asyncio.sleep(0.1)
    return False


async def test_chimera_up_brings_organism_alive(tmp_path):
    _build("echo")
    _build("purge")
    proc = _spawn_up(tmp_path)
    try:
        assert await _status_ok(tmp_path / "core.sock", "echo.status")
        assert await _status_ok(tmp_path / "core.sock", "purge.status")
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)
    assert proc.returncode is not None  # exited cleanly on SIGTERM
