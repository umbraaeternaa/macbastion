"""Tests for lifecycle module (§7.2 FSM + §7.4 heartbeat + §7.5 restart policy).

RED phase: these tests define the contract for core/lifecycle.py before it
exists. Design decisions pinned here (operator-approved):

- ModuleState: StrEnum, 9 values.
- ALLOWED_TRANSITIONS: frozenset[tuple[ModuleState, ModuleState]] allow-list.
- Illegal transition -> InvalidTransitionError (local exception).
- Heartbeat: passive last_seen timestamp + asyncio sweep task.
- Clock: injectable Callable[[], float] (default time.time).
- Storage: Lifecycle owns dict[name, ModuleRecord].
- API: sync FSM (transition / can_transition) + async run() sweep.
- Events: every transition emits module.state_changed via injected broker.
- DEGRADED threshold derived from CoreConfig.heartbeat_dead_threshold - 1.
"""

import asyncio
import time
from collections.abc import Callable

import pytest
from core.broker import EventBroker
from core.config import CoreConfig
from core.lifecycle import (
    InvalidTransitionError,
    Lifecycle,
    ModuleRecord,
    ModuleState,
)

# ---------------------------------------------------------------------------
# Test helpers — deterministic clock + Lifecycle factory
# ---------------------------------------------------------------------------


class FakeClock:
    """Monotonic clock the test advances by hand — no time.sleep anywhere."""

    def __init__(self, start: float = 1000.0) -> None:
        self._t = start

    def now(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self._t += seconds


def _make_lifecycle(
    clock: Callable[[], float] | None = None,
    sweep_interval: float | None = None,
) -> tuple[Lifecycle, EventBroker]:
    """Build a Lifecycle with a fresh broker and default CoreConfig."""
    broker = EventBroker()
    config = CoreConfig()
    lc = Lifecycle(
        config=config,
        broker=broker,
        clock=clock if clock is not None else time.time,
        sweep_interval=sweep_interval,
    )
    return lc, broker


def _bring_to_healthy(lc: Lifecycle, name: str) -> None:
    """Drive the full UNREGISTERED -> STARTING -> REGISTERED -> HEALTHY chain
    and record an initial heartbeat (last_seen = clock())."""
    lc.track(name)
    lc.transition(name, ModuleState.STARTING)
    lc.transition(name, ModuleState.REGISTERED)
    lc.transition(name, ModuleState.HEALTHY)
    lc.heartbeat(name)


# ---------------------------------------------------------------------------
# State enum — 9 StrEnum values
# ---------------------------------------------------------------------------


class TestStateEnum:
    """ModuleState is a StrEnum with exactly the nine §7.2/§7.5 states."""

    def test_is_str_subclass(self) -> None:
        assert issubclass(ModuleState, str)

    def test_has_nine_states(self) -> None:
        assert len(ModuleState) == 9

    def test_all_expected_members_present(self) -> None:
        names = {m.name for m in ModuleState}
        assert names == {
            "UNREGISTERED",
            "STARTING",
            "REGISTERED",
            "HEALTHY",
            "DEGRADED",
            "STOPPING",
            "STOPPED",
            "FAILED",
            "PERMANENTLY_FAILED",
        }

    def test_value_is_lowercase_string(self) -> None:
        assert ModuleState.HEALTHY.value == "healthy"

    def test_member_equals_its_string(self) -> None:
        # StrEnum members compare equal to their string value.
        assert ModuleState.PERMANENTLY_FAILED == "permanently_failed"


# ---------------------------------------------------------------------------
# ModuleRecord — per-module state holder owned by Lifecycle
# ---------------------------------------------------------------------------


class TestModuleRecord:
    """ModuleRecord stores name + state and starts UNREGISTERED."""

    def test_stores_name(self) -> None:
        rec = ModuleRecord(name="vault")
        assert rec.name == "vault"

    def test_default_state_is_unregistered(self) -> None:
        assert ModuleRecord(name="vault").state == ModuleState.UNREGISTERED

    def test_default_last_seen_is_none(self) -> None:
        assert ModuleRecord(name="vault").last_seen is None

    def test_default_restart_count_is_zero(self) -> None:
        assert ModuleRecord(name="vault").restart_count == 0

    def test_state_is_mutable(self) -> None:
        rec = ModuleRecord(name="vault")
        rec.state = ModuleState.HEALTHY
        assert rec.state == ModuleState.HEALTHY


# ---------------------------------------------------------------------------
# Transitions — frozenset allow-list + can_transition()
# ---------------------------------------------------------------------------


class TestTransitions:
    """can_transition() reflects the §7.2 allow-list exactly."""

    def test_allowed_transitions_is_frozenset(self) -> None:
        from core.lifecycle import ALLOWED_TRANSITIONS

        assert isinstance(ALLOWED_TRANSITIONS, frozenset)

    def test_unregistered_to_starting_allowed(self) -> None:
        lc, _ = _make_lifecycle()
        assert lc.can_transition(ModuleState.UNREGISTERED, ModuleState.STARTING)

    def test_starting_to_registered_allowed(self) -> None:
        lc, _ = _make_lifecycle()
        assert lc.can_transition(ModuleState.STARTING, ModuleState.REGISTERED)

    def test_healthy_to_degraded_allowed(self) -> None:
        lc, _ = _make_lifecycle()
        assert lc.can_transition(ModuleState.HEALTHY, ModuleState.DEGRADED)

    def test_registered_to_stopping_allowed(self) -> None:
        # Extends the §7.2 diagram: a just-registered module can be
        # gracefully deregistered before reaching HEALTHY (§7.7).
        lc, _ = _make_lifecycle()
        assert lc.can_transition(ModuleState.REGISTERED, ModuleState.STOPPING)

    def test_degraded_to_healthy_allowed_bidirectional(self) -> None:
        lc, _ = _make_lifecycle()
        assert lc.can_transition(ModuleState.DEGRADED, ModuleState.HEALTHY)

    def test_failed_to_starting_allowed(self) -> None:
        lc, _ = _make_lifecycle()
        assert lc.can_transition(ModuleState.FAILED, ModuleState.STARTING)

    def test_failed_to_permanently_failed_allowed(self) -> None:
        lc, _ = _make_lifecycle()
        assert lc.can_transition(
            ModuleState.FAILED, ModuleState.PERMANENTLY_FAILED
        )

    def test_self_loop_not_allowed(self) -> None:
        lc, _ = _make_lifecycle()
        assert not lc.can_transition(ModuleState.HEALTHY, ModuleState.HEALTHY)

    def test_stopped_to_healthy_not_allowed(self) -> None:
        lc, _ = _make_lifecycle()
        assert not lc.can_transition(ModuleState.STOPPED, ModuleState.HEALTHY)

    def test_unregistered_to_healthy_not_allowed_skips_states(self) -> None:
        lc, _ = _make_lifecycle()
        assert not lc.can_transition(
            ModuleState.UNREGISTERED, ModuleState.HEALTHY
        )


# ---------------------------------------------------------------------------
# Register — UNREGISTERED -> STARTING -> REGISTERED
# ---------------------------------------------------------------------------


class TestRegister:
    """track() births a module; transition() walks the startup chain."""

    def test_track_creates_unregistered_record(self) -> None:
        lc, _ = _make_lifecycle()
        rec = lc.track("vault")
        assert rec.state == ModuleState.UNREGISTERED

    def test_track_makes_module_known(self) -> None:
        lc, _ = _make_lifecycle()
        lc.track("vault")
        assert lc.state_of("vault") == ModuleState.UNREGISTERED

    def test_transition_to_starting(self) -> None:
        lc, _ = _make_lifecycle()
        lc.track("vault")
        lc.transition("vault", ModuleState.STARTING)
        assert lc.state_of("vault") == ModuleState.STARTING

    def test_starting_to_registered(self) -> None:
        lc, _ = _make_lifecycle()
        lc.track("vault")
        lc.transition("vault", ModuleState.STARTING)
        lc.transition("vault", ModuleState.REGISTERED)
        assert lc.state_of("vault") == ModuleState.REGISTERED

    def test_full_chain_to_healthy(self) -> None:
        lc, _ = _make_lifecycle()
        _bring_to_healthy(lc, "vault")
        assert lc.state_of("vault") == ModuleState.HEALTHY


# ---------------------------------------------------------------------------
# Heartbeat — sync reception, sets last_seen via injected clock
# ---------------------------------------------------------------------------


class TestHeartbeat:
    """heartbeat() stamps last_seen from the injected clock."""

    def test_heartbeat_sets_last_seen(self) -> None:
        fake = FakeClock(start=1000.0)
        lc, _ = _make_lifecycle(clock=fake.now)
        lc.track("vault")
        lc.heartbeat("vault")
        assert lc.record("vault").last_seen == 1000.0

    def test_heartbeat_updates_last_seen_on_repeat(self) -> None:
        fake = FakeClock(start=1000.0)
        lc, _ = _make_lifecycle(clock=fake.now)
        lc.track("vault")
        lc.heartbeat("vault")
        fake.advance(15)
        lc.heartbeat("vault")
        assert lc.record("vault").last_seen == 1015.0

    def test_heartbeat_unknown_module_raises(self) -> None:
        lc, _ = _make_lifecycle()
        with pytest.raises(KeyError):
            lc.heartbeat("ghost")


# ---------------------------------------------------------------------------
# Health degradation — HEALTHY <-> DEGRADED driven by sweep + clock
# ---------------------------------------------------------------------------


class TestHealthDegradation:
    """sweep_once() degrades/fails/recovers based on missed heartbeats."""

    def test_fresh_heartbeat_stays_healthy(self) -> None:
        fake = FakeClock()
        lc, _ = _make_lifecycle(clock=fake.now)
        _bring_to_healthy(lc, "vault")
        fake.advance(5)  # missed = 0
        lc.sweep_once()
        assert lc.state_of("vault") == ModuleState.HEALTHY

    def test_two_missed_marks_degraded(self) -> None:
        fake = FakeClock()
        lc, _ = _make_lifecycle(clock=fake.now)
        _bring_to_healthy(lc, "vault")
        fake.advance(20)  # missed = 2 -> DEGRADED
        lc.sweep_once()
        assert lc.state_of("vault") == ModuleState.DEGRADED

    def test_three_missed_marks_failed(self) -> None:
        fake = FakeClock()
        lc, _ = _make_lifecycle(clock=fake.now)
        _bring_to_healthy(lc, "vault")
        fake.advance(30)  # missed = 3 -> FAILED
        lc.sweep_once()
        assert lc.state_of("vault") == ModuleState.FAILED

    def test_degraded_recovers_to_healthy_on_fresh_heartbeat(self) -> None:
        fake = FakeClock()
        lc, _ = _make_lifecycle(clock=fake.now)
        _bring_to_healthy(lc, "vault")
        fake.advance(20)
        lc.sweep_once()
        assert lc.state_of("vault") == ModuleState.DEGRADED
        lc.heartbeat("vault")  # last_seen = now (fresh)
        lc.sweep_once()
        assert lc.state_of("vault") == ModuleState.HEALTHY

    def test_repeated_sweep_is_idempotent(self) -> None:
        fake = FakeClock()
        lc, _ = _make_lifecycle(clock=fake.now)
        _bring_to_healthy(lc, "vault")
        fake.advance(20)
        lc.sweep_once()
        lc.sweep_once()  # must not raise on no-op (no self-transition)
        assert lc.state_of("vault") == ModuleState.DEGRADED

    def test_sweep_ignores_modules_not_yet_healthy(self) -> None:
        fake = FakeClock()
        lc, _ = _make_lifecycle(clock=fake.now)
        lc.track("vault")
        lc.transition("vault", ModuleState.STARTING)
        lc.transition("vault", ModuleState.REGISTERED)  # last_seen still None
        fake.advance(100)
        lc.sweep_once()
        assert lc.state_of("vault") == ModuleState.REGISTERED

    def test_degraded_threshold_is_dead_threshold_minus_one(self) -> None:
        lc, _ = _make_lifecycle()
        config = CoreConfig()
        assert lc.degraded_threshold == config.heartbeat_dead_threshold - 1


# ---------------------------------------------------------------------------
# Graceful stop — HEALTHY -> STOPPING -> STOPPED
# ---------------------------------------------------------------------------


class TestStopGraceful:
    """Graceful shutdown walks HEALTHY -> STOPPING -> STOPPED; STOPPED is terminal."""

    def test_healthy_to_stopping(self) -> None:
        lc, _ = _make_lifecycle()
        _bring_to_healthy(lc, "vault")
        lc.transition("vault", ModuleState.STOPPING)
        assert lc.state_of("vault") == ModuleState.STOPPING

    def test_stopping_to_stopped(self) -> None:
        lc, _ = _make_lifecycle()
        _bring_to_healthy(lc, "vault")
        lc.transition("vault", ModuleState.STOPPING)
        lc.transition("vault", ModuleState.STOPPED)
        assert lc.state_of("vault") == ModuleState.STOPPED

    def test_stopped_is_terminal(self) -> None:
        lc, _ = _make_lifecycle()
        _bring_to_healthy(lc, "vault")
        lc.transition("vault", ModuleState.STOPPING)
        lc.transition("vault", ModuleState.STOPPED)
        with pytest.raises(InvalidTransitionError):
            lc.transition("vault", ModuleState.HEALTHY)


# ---------------------------------------------------------------------------
# Failure — any live state -> FAILED
# ---------------------------------------------------------------------------


class TestFailure:
    """FAILED is reachable from live states (crash / kill / heartbeat lost)."""

    def test_healthy_to_failed(self) -> None:
        lc, _ = _make_lifecycle()
        _bring_to_healthy(lc, "vault")
        lc.transition("vault", ModuleState.FAILED)
        assert lc.state_of("vault") == ModuleState.FAILED

    def test_starting_to_failed(self) -> None:
        lc, _ = _make_lifecycle()
        lc.track("vault")
        lc.transition("vault", ModuleState.STARTING)
        lc.transition("vault", ModuleState.FAILED)
        assert lc.state_of("vault") == ModuleState.FAILED

    def test_degraded_to_failed(self) -> None:
        lc, _ = _make_lifecycle()
        _bring_to_healthy(lc, "vault")
        lc.transition("vault", ModuleState.DEGRADED)
        lc.transition("vault", ModuleState.FAILED)
        assert lc.state_of("vault") == ModuleState.FAILED


# ---------------------------------------------------------------------------
# Restart policy — FAILED -> STARTING with backoff, cap -> PERMANENTLY_FAILED
# ---------------------------------------------------------------------------


class TestRestartPolicy:
    """restart() cycles FAILED -> STARTING up to the cap, then PERMANENTLY_FAILED."""

    def test_restart_moves_failed_to_starting(self) -> None:
        lc, _ = _make_lifecycle()
        _bring_to_healthy(lc, "vault")
        lc.transition("vault", ModuleState.FAILED)
        lc.restart("vault")
        assert lc.state_of("vault") == ModuleState.STARTING

    def test_restart_increments_restart_count(self) -> None:
        lc, _ = _make_lifecycle()
        _bring_to_healthy(lc, "vault")
        lc.transition("vault", ModuleState.FAILED)
        lc.restart("vault")
        assert lc.record("vault").restart_count == 1

    def test_backoff_delay_sequence(self) -> None:
        lc, _ = _make_lifecycle()
        delays = [lc.backoff_delay(n) for n in range(1, 7)]
        assert delays == [1, 2, 4, 8, 30, 30]

    def test_exceeding_max_restarts_marks_permanently_failed(self) -> None:
        fake = FakeClock()
        lc, _ = _make_lifecycle(clock=fake.now)
        _bring_to_healthy(lc, "vault")
        config = CoreConfig()  # restart_max_per_hour default 5
        # Five restarts within the hour; each followed by a fresh crash.
        for _ in range(config.restart_max_per_hour):
            lc.transition("vault", ModuleState.FAILED)
            lc.restart("vault")  # -> STARTING
            fake.advance(1)
        # Sixth crash + restart attempt exceeds the cap.
        lc.transition("vault", ModuleState.FAILED)
        lc.restart("vault")
        assert lc.state_of("vault") == ModuleState.PERMANENTLY_FAILED

    def test_restarts_outside_window_do_not_count(self) -> None:
        fake = FakeClock()
        lc, _ = _make_lifecycle(clock=fake.now)
        _bring_to_healthy(lc, "vault")
        config = CoreConfig()
        for _ in range(config.restart_max_per_hour):
            lc.transition("vault", ModuleState.FAILED)
            lc.restart("vault")
            fake.advance(1)
        fake.advance(3601)  # older restarts fall out of the rolling hour
        lc.transition("vault", ModuleState.FAILED)
        lc.restart("vault")
        assert lc.state_of("vault") == ModuleState.STARTING


# ---------------------------------------------------------------------------
# PERMANENTLY_FAILED — terminal, no outgoing transitions
# ---------------------------------------------------------------------------


class TestPermanentlyFailed:
    """PERMANENTLY_FAILED is terminal; nothing leaves it."""

    def test_no_transition_out_is_allowed(self) -> None:
        lc, _ = _make_lifecycle()
        for target in ModuleState:
            assert not lc.can_transition(ModuleState.PERMANENTLY_FAILED, target)

    def test_transition_out_raises(self) -> None:
        lc, _ = _make_lifecycle()
        lc.track("vault")
        # Walk to PERMANENTLY_FAILED through legal edges.
        lc.transition("vault", ModuleState.STARTING)
        lc.transition("vault", ModuleState.FAILED)
        lc.transition("vault", ModuleState.PERMANENTLY_FAILED)
        with pytest.raises(InvalidTransitionError):
            lc.transition("vault", ModuleState.STARTING)


# ---------------------------------------------------------------------------
# Heartbeat sweep — async monitor task
# ---------------------------------------------------------------------------


class TestHeartbeatSweep:
    """run() loops sweep_once() and cancels cleanly."""

    async def test_run_task_cancels_cleanly(self) -> None:
        lc, _ = _make_lifecycle(sweep_interval=0.01)
        task = asyncio.create_task(lc.run())
        await asyncio.sleep(0.02)
        assert not task.done()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    async def test_run_marks_stale_module_degraded(self) -> None:
        fake = FakeClock()
        lc, _ = _make_lifecycle(clock=fake.now, sweep_interval=0.01)
        _bring_to_healthy(lc, "vault")
        fake.advance(20)  # 2 missed -> DEGRADED
        task = asyncio.create_task(lc.run())
        try:
            for _ in range(100):
                if lc.state_of("vault") == ModuleState.DEGRADED:
                    break
                await asyncio.sleep(0.01)
            assert lc.state_of("vault") == ModuleState.DEGRADED
        finally:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

    async def test_run_marks_stale_module_failed(self) -> None:
        fake = FakeClock()
        lc, _ = _make_lifecycle(clock=fake.now, sweep_interval=0.01)
        _bring_to_healthy(lc, "vault")
        fake.advance(30)  # 3 missed -> FAILED
        task = asyncio.create_task(lc.run())
        try:
            for _ in range(100):
                if lc.state_of("vault") == ModuleState.FAILED:
                    break
                await asyncio.sleep(0.01)
            assert lc.state_of("vault") == ModuleState.FAILED
        finally:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task


# ---------------------------------------------------------------------------
# Events — every transition publishes module.state_changed via broker
# ---------------------------------------------------------------------------


class TestEvents:
    """transition() emits one module.state_changed event per transition."""

    def test_transition_publishes_event(self) -> None:
        lc, broker = _make_lifecycle()
        lc.track("vault")
        sub = broker.subscribe(["module.state_changed"])
        lc.transition("vault", ModuleState.STARTING)
        assert sub.get_nowait().topic == "module.state_changed"

    def test_event_payload_carries_module_name(self) -> None:
        lc, broker = _make_lifecycle()
        lc.track("vault")
        sub = broker.subscribe(["module.state_changed"])
        lc.transition("vault", ModuleState.STARTING)
        assert sub.get_nowait().payload["module"] == "vault"

    def test_event_payload_carries_from_and_to(self) -> None:
        lc, broker = _make_lifecycle()
        lc.track("vault")
        sub = broker.subscribe(["module.state_changed"])
        lc.transition("vault", ModuleState.STARTING)
        payload = sub.get_nowait().payload
        assert payload["from"] == ModuleState.UNREGISTERED
        assert payload["to"] == ModuleState.STARTING

    def test_multiple_transitions_emit_in_order(self) -> None:
        lc, broker = _make_lifecycle()
        lc.track("vault")
        sub = broker.subscribe(["module.state_changed"])
        lc.transition("vault", ModuleState.STARTING)
        lc.transition("vault", ModuleState.REGISTERED)
        first = sub.get_nowait().payload["to"]
        second = sub.get_nowait().payload["to"]
        assert (first, second) == (ModuleState.STARTING, ModuleState.REGISTERED)

    def test_failed_transition_emits_no_event(self) -> None:
        lc, broker = _make_lifecycle()
        lc.track("vault")  # state UNREGISTERED
        sub = broker.subscribe(["module.state_changed"])
        with pytest.raises(InvalidTransitionError):
            lc.transition("vault", ModuleState.HEALTHY)  # illegal skip
        with pytest.raises(asyncio.QueueEmpty):
            sub.get_nowait()


# ---------------------------------------------------------------------------
# Edge cases — names, duplicates, unknowns, illegal transitions
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Boundary conditions that often hide bugs."""

    def test_track_empty_name_raises(self) -> None:
        lc, _ = _make_lifecycle()
        with pytest.raises(ValueError, match="name"):
            lc.track("")

    def test_track_duplicate_name_raises(self) -> None:
        lc, _ = _make_lifecycle()
        lc.track("vault")
        with pytest.raises(ValueError, match="already"):
            lc.track("vault")

    def test_unicode_name_works(self) -> None:
        lc, _ = _make_lifecycle()
        lc.track("модуль-сховище")
        assert lc.state_of("модуль-сховище") == ModuleState.UNREGISTERED

    def test_transition_unknown_module_raises(self) -> None:
        lc, _ = _make_lifecycle()
        with pytest.raises(KeyError):
            lc.transition("ghost", ModuleState.STARTING)

    def test_state_of_unknown_module_raises(self) -> None:
        lc, _ = _make_lifecycle()
        with pytest.raises(KeyError):
            lc.state_of("ghost")

    def test_illegal_transition_message_names_states(self) -> None:
        lc, _ = _make_lifecycle()
        lc.track("vault")  # UNREGISTERED
        with pytest.raises(InvalidTransitionError, match="unregistered"):
            lc.transition("vault", ModuleState.STOPPED)
