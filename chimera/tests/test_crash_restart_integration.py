"""Crash-restart integration (CR-1) — an abruptly-killed module (no graceful deregister)
is detected by core and marked FAILED, which is the restartable state the supervisor acts
on (SV-5'b). Marked integration (subprocess + sockets); needs a short --basetemp.

This pins the NEW behaviour (crash -> FAILED). The FAILED -> re-spawn half is covered by
the supervisor autonomy unit tests; in a live `chimera up` the two compose into self-heal.
"""

import asyncio
import subprocess
from pathlib import Path

import pytest
from core.config import CoreConfig
from core.lifecycle import ModuleState

pytestmark = pytest.mark.integration

CHIMERA = Path(__file__).resolve().parent.parent


def _build(name):
    result = subprocess.run(
        ["make", "-C", str(CHIMERA / "modules" / name)], capture_output=True, text=True
    )
    if result.returncode != 0:
        pytest.skip(f"{name} build failed:\n{result.stderr}")
    binary = CHIMERA / "modules" / name / name
    if not binary.exists():
        pytest.skip(f"{name} binary not produced")
    return binary


def _spawn(binary, socket_dir):
    return subprocess.Popen(
        [str(binary)],
        env={"CHIMERA_SOCKET_DIR": str(socket_dir), "PATH": "/usr/bin:/bin"},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


async def _wait(pred, timeout_s=8.0):
    for _ in range(int(timeout_s / 0.05)):
        if pred():
            return True
        await asyncio.sleep(0.05)
    return False


async def test_crash_marks_module_failed(tmp_path):
    from core.__main__ import build_core

    binary = _build("echo")
    server = build_core(CoreConfig.model_validate({"socket_dir": str(tmp_path)}))
    await server.start()
    proc = _spawn(binary, tmp_path)
    try:
        assert await _wait(lambda: server._registry.is_registered("echo"))
        proc.kill()  # abrupt crash — no graceful core.deregister
        proc.wait(timeout=3)
        assert await _wait(lambda: server._lifecycle.state_of("echo") == ModuleState.FAILED)
    finally:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=3)
        await server.stop()
