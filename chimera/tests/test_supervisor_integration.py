"""Supervisor integration (SV-2) — the real Supervisor brings the ECHO + PURGE C daemons
up against a live core, in dependency waves, and tears them down. Marked integration
(real sockets / subprocesses); needs a short --basetemp (AF_UNIX). RED until GREEN.
"""

import subprocess
from pathlib import Path

import pytest
from core.config import CoreConfig

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


def _spawner(bins, socket_dir, procs):
    def spawn(spec):
        proc = subprocess.Popen(
            [str(bins[spec.name])],
            env={"CHIMERA_SOCKET_DIR": str(socket_dir), "PATH": "/usr/bin:/bin"},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        procs.append(proc)
        return proc

    return spawn


async def test_supervisor_brings_up_modules(tmp_path):
    from core.__main__ import build_core
    from core.supervisor import ModuleSpec, Supervisor

    bins = {"echo": _build("echo"), "purge": _build("purge")}
    server = build_core(CoreConfig.model_validate({"socket_dir": str(tmp_path)}))
    await server.start()
    procs: list = []
    sup = Supervisor(
        [ModuleSpec("echo"), ModuleSpec("purge")],
        spawn=_spawner(bins, tmp_path, procs),
        is_registered=server._registry.is_registered,
        wave_timeout=6.0,
    )
    try:
        await sup.up()
        assert sup.failed == set()
        assert server._registry.is_registered("echo")
        assert server._registry.is_registered("purge")
    finally:
        await sup.down()
        for proc in procs:
            proc.wait(timeout=3)
        await server.stop()
