"""CHIMERA module supervisor (SV-2) — RED stub.

Dependency-ordered module launch (§7.3): compute startup waves from each module's
depends_on, then bring modules up wave by wave, each wave waiting for the previous to
register. Launch + registration-check are injected (DI) so the wave logic is testable
without real processes. The logic raises NotImplementedError until GREEN (MANIFESTO §4);
the dataclass is real so tests can construct specs.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ModuleSpec:
    """A supervised module: its name and the modules it depends on."""

    name: str
    depends_on: tuple[str, ...] = ()


# Modules with a runnable launcher today; grows as more modules become launchable.
CHIMERA_MODULES: tuple[ModuleSpec, ...] = (
    ModuleSpec("echo"),
    ModuleSpec("purge"),
)


class SupervisedProc(Protocol):
    """Minimal process handle the supervisor needs (subprocess.Popen satisfies this)."""

    def terminate(self) -> None: ...


def topological_waves(specs: Sequence[ModuleSpec]) -> list[list[ModuleSpec]]:
    """Layer specs into dependency waves (a module follows all its deps). Raises
    ValueError on a cycle or an unknown dependency."""
    raise NotImplementedError("topological_waves — to be implemented (SV-2)")


class Supervisor:
    """Brings modules up in dependency waves and tears them down in reverse."""

    def __init__(
        self,
        specs: Sequence[ModuleSpec],
        *,
        spawn: Callable[[ModuleSpec], SupervisedProc],
        is_registered: Callable[[str], bool],
        wave_timeout: float = 5.0,
    ) -> None:
        self._specs = list(specs)
        self._spawn = spawn
        self._is_registered = is_registered
        self._wave_timeout = wave_timeout
        self._procs: dict[str, SupervisedProc] = {}
        self._failed: set[str] = set()

    @property
    def failed(self) -> set[str]:
        return self._failed

    async def up(self) -> None:
        """Launch every module wave by wave; a wave waits for the previous to register.
        A module that never registers within wave_timeout is marked failed, not awaited
        forever (§7.3 fail-closed, not fail-stuck)."""
        raise NotImplementedError("Supervisor.up — to be implemented (SV-2)")

    async def down(self) -> None:
        """Terminate spawned modules in reverse launch order."""
        raise NotImplementedError("Supervisor.down — to be implemented (SV-2)")
