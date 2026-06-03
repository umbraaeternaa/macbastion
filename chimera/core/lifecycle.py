"""Module lifecycle state machine (§7.2 + §7.4 heartbeat + §7.5 restart).

Core's view of every module: a finite-state machine over nine states
(§7.2), liveness derived from heartbeat timestamps (§7.4), and an
exponential-backoff restart policy with a rolling-hour cap (§7.5).

Design (operator-approved, pinned by tests/test_lifecycle.py):
- States: a 9-value StrEnum.
- Transitions: an explicit frozenset allow-list; an illegal move raises
  InvalidTransitionError — a local exception, mirroring broker's
  SubscriptionClosedError (no new wire-facing ChimeraError codes).
- Liveness: a passive last_seen timestamp plus an async sweep that derives
  HEALTHY / DEGRADED / FAILED from the missed-heartbeat count. The clock is
  injected (Callable[[], float]) so timing is deterministic under test.
- Storage: Lifecycle owns dict[name, ModuleRecord]; nothing is persisted
  (§7.8 — the registry is rebuilt from re-registration, never from disk).
- Every transition emits one `module.state_changed` event via the injected
  broker (§6.6).

Governing rule (§7.1, invariant I3): on uncertainty the FSM moves toward
MORE closed, never toward open. This module never triggers a destructive
action (I4) — it only changes a module's recorded state.
"""

import asyncio
import time
from collections.abc import Callable
from enum import StrEnum
from typing import Any, ClassVar

from pydantic import BaseModel, Field

from core.broker import Event, EventBroker
from core.config import CoreConfig


class ModuleState(StrEnum):
    """The nine lifecycle states a module can occupy (§7.2)."""

    UNREGISTERED = "unregistered"
    STARTING = "starting"
    REGISTERED = "registered"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    PERMANENTLY_FAILED = "permanently_failed"


# Allowed (from, to) edges: the §7.2 diagram plus the §7.5 restart paths.
# STOPPED and PERMANENTLY_FAILED are terminal (no outgoing edges); a clean
# restart always re-enters via FAILED -> STARTING. No self-loops.
# REGISTERED -> STOPPING extends the §7.2 diagram so a module can be
# gracefully deregistered before it ever reaches HEALTHY (§7.7).
ALLOWED_TRANSITIONS: frozenset[tuple[ModuleState, ModuleState]] = frozenset(
    {
        (ModuleState.UNREGISTERED, ModuleState.STARTING),
        (ModuleState.STARTING, ModuleState.REGISTERED),
        (ModuleState.STARTING, ModuleState.FAILED),
        (ModuleState.REGISTERED, ModuleState.HEALTHY),
        (ModuleState.REGISTERED, ModuleState.FAILED),
        (ModuleState.REGISTERED, ModuleState.STOPPING),
        (ModuleState.HEALTHY, ModuleState.DEGRADED),
        (ModuleState.DEGRADED, ModuleState.HEALTHY),
        (ModuleState.HEALTHY, ModuleState.STOPPING),
        (ModuleState.DEGRADED, ModuleState.STOPPING),
        (ModuleState.HEALTHY, ModuleState.FAILED),
        (ModuleState.DEGRADED, ModuleState.FAILED),
        (ModuleState.STOPPING, ModuleState.STOPPED),
        (ModuleState.STOPPING, ModuleState.FAILED),
        (ModuleState.FAILED, ModuleState.STARTING),
        (ModuleState.FAILED, ModuleState.PERMANENTLY_FAILED),
    }
)


class InvalidTransitionError(Exception):
    """Raised when a requested transition is not in ALLOWED_TRANSITIONS."""


class ModuleRecord(BaseModel):
    """Mutable per-module bookkeeping owned by Lifecycle.

    Not frozen: state, last_seen, and the restart counters mutate in place
    across a module's life. Persisted nowhere (§7.8).
    """

    name: str
    state: ModuleState = ModuleState.UNREGISTERED
    last_seen: float | None = None
    restart_count: int = 0
    restart_times: list[float] = Field(default_factory=list)


class Lifecycle:
    """Finite-state lifecycle manager for every module known to core.

    Sync FSM (track / transition / can_transition) plus a passive heartbeat
    monitor (heartbeat / sweep_once / run) and the §7.5 restart policy.
    """

    STATE_CHANGED_TOPIC: ClassVar[str] = "module.state_changed"
    RESTART_WINDOW_S: ClassVar[int] = 3600
    BACKOFF_CAP_S: ClassVar[float] = 30.0
    # Only these states are subject to heartbeat liveness; the rest are stable.
    _LIVENESS_STATES: ClassVar[frozenset[ModuleState]] = frozenset(
        {ModuleState.HEALTHY, ModuleState.DEGRADED}
    )

    def __init__(
        self,
        config: CoreConfig,
        broker: EventBroker,
        clock: Callable[[], float] = time.time,
        sweep_interval: float | None = None,
    ) -> None:
        self._config = config
        self._broker = broker
        self._clock = clock
        self._sweep_interval = (
            float(config.heartbeat_interval_s)
            if sweep_interval is None
            else sweep_interval
        )
        self._records: dict[str, ModuleRecord] = {}

    # -- introspection ----------------------------------------------------

    @property
    def degraded_threshold(self) -> int:
        """Missed-heartbeat count that marks DEGRADED (§7.4)."""
        return self._config.heartbeat_dead_threshold - 1

    def record(self, name: str) -> ModuleRecord:
        """Return a module's record. Raises KeyError if unknown."""
        return self._records[name]

    def state_of(self, name: str) -> ModuleState:
        """Return a module's current state. Raises KeyError if unknown."""
        return self._records[name].state

    # -- registration -----------------------------------------------------

    def track(self, name: str) -> ModuleRecord:
        """Begin tracking a module in UNREGISTERED. Births its record."""
        if not name:
            raise ValueError("module name must be non-empty")
        if name in self._records:
            raise ValueError(f"module already tracked: {name}")
        rec = ModuleRecord(name=name)
        self._records[name] = rec
        return rec

    # -- FSM core ---------------------------------------------------------

    def can_transition(self, src: ModuleState, dst: ModuleState) -> bool:
        """True iff (src, dst) is an allowed edge (§7.2 allow-list)."""
        return (src, dst) in ALLOWED_TRANSITIONS

    def transition(self, name: str, to_state: ModuleState) -> None:
        """Move a module to to_state, emitting module.state_changed.

        Raises KeyError if the module is unknown, InvalidTransitionError if
        the edge is not in the allow-list. No event is emitted on a rejected
        transition.
        """
        rec = self._records[name]
        src = rec.state
        if (src, to_state) not in ALLOWED_TRANSITIONS:
            raise InvalidTransitionError(
                f"illegal transition: {src} -> {to_state} (module {name})"
            )
        rec.state = to_state
        self._emit(name, src, to_state)

    def _emit(self, name: str, src: ModuleState, dst: ModuleState) -> None:
        """Publish a single module.state_changed event for one transition."""
        payload: dict[str, Any] = {"module": name, "from": src, "to": dst}
        self._broker.publish(
            Event(topic=self.STATE_CHANGED_TOPIC, payload=payload)
        )

    # -- heartbeat & liveness --------------------------------------------

    def heartbeat(self, name: str) -> None:
        """Record a liveness heartbeat (last_seen = now). KeyError if unknown."""
        self._records[name].last_seen = self._clock()

    def sweep_once(self) -> None:
        """Evaluate every live module's heartbeat freshness once (§7.4).

        Only HEALTHY/DEGRADED modules are subject to liveness; the rest are
        stable. Idempotent: a module already in its desired state is left
        untouched (no self-transition).
        """
        now = self._clock()
        interval = self._config.heartbeat_interval_s
        for rec in list(self._records.values()):
            if rec.state not in self._LIVENESS_STATES:
                continue
            if rec.last_seen is None:
                continue
            missed = int((now - rec.last_seen) // interval)
            desired = self._desired_state(missed)
            if desired != rec.state:
                self.transition(rec.name, desired)

    def _desired_state(self, missed: int) -> ModuleState:
        """Map a missed-heartbeat count to its target state (§7.4)."""
        if missed >= self._config.heartbeat_dead_threshold:
            return ModuleState.FAILED
        if missed >= self.degraded_threshold:
            return ModuleState.DEGRADED
        return ModuleState.HEALTHY

    async def run(self) -> None:
        """Periodic sweep loop. Cancel the task to stop it (§7.4 monitor)."""
        while True:
            self.sweep_once()
            await asyncio.sleep(self._sweep_interval)

    # -- restart policy ---------------------------------------------------

    def restart(self, name: str) -> None:
        """Attempt a restart (§7.5).

        FAILED -> STARTING while the module is under the rolling-hour cap;
        FAILED -> PERMANENTLY_FAILED once MAX_RESTARTS within the last hour
        is reached. Raises KeyError if unknown, InvalidTransitionError if the
        module is not in a restartable state.
        """
        rec = self._records[name]
        now = self._clock()
        rec.restart_times = [
            t for t in rec.restart_times if now - t < self.RESTART_WINDOW_S
        ]
        if len(rec.restart_times) >= self._config.restart_max_per_hour:
            self.transition(name, ModuleState.PERMANENTLY_FAILED)
            return
        rec.restart_times.append(now)
        rec.restart_count += 1
        self.transition(name, ModuleState.STARTING)

    def backoff_delay(self, attempt: int) -> float:
        """Backoff for the n-th restart: 1, 2, 4, 8, then 30s capped (§7.5)."""
        if attempt < 1:
            raise ValueError("attempt must be >= 1")
        if attempt <= 4:
            return float(2 ** (attempt - 1))
        return self.BACKOFF_CAP_S
