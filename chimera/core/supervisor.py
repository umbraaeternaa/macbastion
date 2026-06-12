"""CHIMERA module supervisor (§7.3 dependency-ordered launch + §7.5 process restart).

Computes startup waves from each module's depends_on and brings modules up wave by wave,
each wave waiting for the previous to register; tears down in reverse. Launch +
registration-check are injected (DI) so the wave logic is testable without real processes.

The §7.5 restart DECISION (budget, backoff, FSM) lives in core.lifecycle — the single
source of truth. The supervisor's role is the process ACTION: on a module reaching FAILED,
it asks lifecycle to restart and, if allowed (-> STARTING), re-spawns the OS process.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from core.lifecycle import Lifecycle, ModuleState


@dataclass(frozen=True)
class ModuleSpec:
    """A supervised module: its name and the modules it depends on."""

    name: str
    depends_on: tuple[str, ...] = ()
    python: bool = False  # True -> launched as `python -m <name>`, not a native binary


# Modules with a runnable launcher today; grows as more modules become launchable.
CHIMERA_MODULES: tuple[ModuleSpec, ...] = (
    ModuleSpec("echo"),
    ModuleSpec("purge"),
)


class SupervisedProc(Protocol):
    """Minimal process handle the supervisor needs (subprocess.Popen satisfies this)."""

    def terminate(self) -> None: ...
    def kill(self) -> None: ...
    def poll(self) -> int | None: ...


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


class Supervisor:
    """Brings modules up in dependency waves and tears them down in reverse."""

    def __init__(
        self,
        specs: Sequence[ModuleSpec],
        *,
        spawn: Callable[[ModuleSpec], SupervisedProc],
        is_registered: Callable[[str], bool],
        wave_timeout: float = 5.0,
        shutdown_grace: float = 5.0,
    ) -> None:
        self._specs = list(specs)
        self._spawn = spawn
        self._is_registered = is_registered
        self._wave_timeout = wave_timeout
        self._shutdown_grace = shutdown_grace
        self._procs: dict[str, SupervisedProc] = {}
        self._failed: set[str] = set()

    @property
    def failed(self) -> set[str]:
        return self._failed

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
        """Graceful shutdown (§7.7): SIGTERM every module (reverse launch order), wait up to
        shutdown_grace for them to exit, then SIGKILL any straggler still running."""
        names = list(reversed(self._procs))
        for name in names:
            self._procs[name].terminate()
        steps = max(1, int(self._shutdown_grace / 0.05))
        for _ in range(steps):
            if all(self._procs[n].poll() is not None for n in names):
                return
            await asyncio.sleep(0.05)
        for name in names:
            if self._procs[name].poll() is None:
                self._procs[name].kill()

    async def purge_kill(self, grace: float = 0.5) -> list[str]:
        """Emergency choreography (§5.8 step 1): broadcast already sent (core publishes
        purge.imminent); give modules a brief grace to zero their own keys, then SIGKILL every
        supervised proc still alive — ack-or-die. Returns the names force-killed. This is the
        force fallback; modules that zeroed + exited on their own are skipped."""
        if grace > 0:
            await asyncio.sleep(grace)
        killed: list[str] = []
        for name, proc in self._procs.items():
            if proc.poll() is None:
                proc.kill()
                killed.append(name)
        return killed

    def handle_failure(self, name: str, lifecycle: Lifecycle) -> bool:
        """A supervised module reached FAILED: delegate the restart decision to lifecycle
        (§7.5 budget/backoff/FSM — the single source of truth); if it transitions to
        STARTING, re-spawn the OS process. Returns True iff the process was respawned."""
        spec = next((s for s in self._specs if s.name == name), None)
        if spec is None:
            return False
        try:
            if lifecycle.state_of(name) != ModuleState.FAILED:
                return False
        except KeyError:
            return False
        lifecycle.restart(name)  # FAILED -> STARTING (within budget) or PERMANENTLY_FAILED
        if lifecycle.state_of(name) == ModuleState.STARTING:
            self._procs[name] = self._spawn(spec)
            return True
        return False

    def on_state_changed(self, payload: Mapping[str, object], lifecycle: Lifecycle) -> bool:
        """Broker hook for module.state_changed: restart on a transition TO FAILED,
        ignore every other transition. Returns whether a restart was attempted."""
        if payload.get("to") != ModuleState.FAILED:
            return False
        module = payload.get("module")
        if not isinstance(module, str):
            return False
        return self.handle_failure(module, lifecycle)
