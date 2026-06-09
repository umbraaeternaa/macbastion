"""CHIMERA module supervisor (SV-2) — RED stub.

Dependency-ordered module launch (§7.3): compute startup waves from each module's
depends_on, then bring modules up wave by wave, each wave waiting for the previous to
register. Launch + registration-check are injected (DI) so the wave logic is testable
without real processes. The logic raises NotImplementedError until GREEN (MANIFESTO §4);
the dataclass is real so tests can construct specs.
"""

from __future__ import annotations

import asyncio
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
    by_name = {s.name: s for s in specs}
    deps = {s.name: set(s.depends_on) for s in specs}
    for name, ds in deps.items():
        for d in ds:
            if d not in by_name:
                raise ValueError(f"unknown dependency {d!r} for module {name!r}")
    done: set[str] = set()
    remaining = set(by_name)
    waves: list[list[ModuleSpec]] = []
    while remaining:
        ready = sorted(n for n in remaining if deps[n] <= done)
        if not ready:
            raise ValueError(f"dependency cycle among {sorted(remaining)}")
        waves.append([by_name[n] for n in ready])
        done.update(ready)
        remaining.difference_update(ready)
    return waves


def backoff_delay(attempt: int) -> float:
    """§7.5 restart backoff: attempts 1-4 -> 1/2/4/8s, attempt 5+ capped at 30s."""
    raise NotImplementedError("backoff_delay — to be implemented (SV-3)")


class RestartTracker:
    """Tracks a module's restart timestamps within a rolling window (§7.5)."""

    def __init__(self, max_restarts: int = 5, window_s: float = 3600.0) -> None:
        self._max = max_restarts
        self._window = window_s
        self._times: list[float] = []

    def attempts(self, now: float) -> int:
        raise NotImplementedError("RestartTracker.attempts — to be implemented (SV-3)")

    def allowed(self, now: float) -> bool:
        raise NotImplementedError("RestartTracker.allowed — to be implemented (SV-3)")

    def record(self, now: float) -> None:
        raise NotImplementedError("RestartTracker.record — to be implemented (SV-3)")


class Supervisor:
    """Brings modules up in dependency waves and tears them down in reverse."""

    def __init__(
        self,
        specs: Sequence[ModuleSpec],
        *,
        spawn: Callable[[ModuleSpec], SupervisedProc],
        is_registered: Callable[[str], bool],
        wave_timeout: float = 5.0,
        max_restarts: int = 5,
        restart_window_s: float = 3600.0,
    ) -> None:
        self._specs = list(specs)
        self._spawn = spawn
        self._is_registered = is_registered
        self._wave_timeout = wave_timeout
        self._max_restarts = max_restarts
        self._restart_window_s = restart_window_s
        self._procs: dict[str, SupervisedProc] = {}
        self._failed: set[str] = set()
        self._trackers: dict[str, RestartTracker] = {}
        self._dead: set[str] = set()

    @property
    def failed(self) -> set[str]:
        return self._failed

    @property
    def dead(self) -> set[str]:
        """Modules that exhausted their restart budget (PERMANENTLY_FAILED, §7.5)."""
        return self._dead

    def restart(self, name: str, *, now: float) -> float | None:
        """Restart a failed module if its budget allows (§7.5). Returns the backoff delay
        the caller should wait before the module is expected live, or None if the module
        is now permanently failed (gave up)."""
        raise NotImplementedError("Supervisor.restart — to be implemented (SV-3)")

    async def up(self) -> None:
        """Launch every module wave by wave; a wave waits for the previous to register.
        A module that never registers within wave_timeout is marked failed, not awaited
        forever (§7.3 fail-closed, not fail-stuck)."""
        for wave in topological_waves(self._specs):
            for spec in wave:
                self._procs[spec.name] = self._spawn(spec)
            for spec in wave:
                if not await self._await_registered(spec.name):
                    self._failed.add(spec.name)

    async def _await_registered(self, name: str) -> bool:
        steps = max(1, int(self._wave_timeout / 0.05))
        for _ in range(steps):
            if self._is_registered(name):
                return True
            await asyncio.sleep(0.05)
        return self._is_registered(name)

    async def down(self) -> None:
        """Terminate spawned modules in reverse launch order."""
        for name in reversed(list(self._procs)):
            self._procs[name].terminate()
            await asyncio.sleep(0)
