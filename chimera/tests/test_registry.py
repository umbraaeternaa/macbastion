"""Tests for registry module (§6.7 capabilities + §7.2 lifecycle states).

RED phase: defines the contract for core/registry.py before it exists.
Decisions pinned here (operator-approved):

- Storage: dict[str, ModuleEntry]; ModuleEntry is a frozen BaseModel
  (version, methods: frozenset, events: frozenset, depends_on: tuple).
- Registration: re-register overwrites (last-write-wins, §7.8 reconnect).
- Capability matching: prefix-split "vault.unlock" -> "vault", O(1) frozenset.
- Integration: Registry composes Lifecycle and DRIVES it (orchestrating);
  status is delegated to lifecycle.state_of(), never duplicated.
- Events: every register/deregister emits module.registered / .deregistered
  via the injected broker (separate from lifecycle's module.state_changed).
- API: sync. Auth lives in the server, not here (registry = facts only).
- DAG: registry only stores depends_on and exposes dependency_graph().

register() state path (sub-D8):
  untracked              -> track + STARTING + REGISTERED (2 state_changed)
  STARTING               -> REGISTERED (1 state_changed)
  REGISTERED/HEALTHY/DEGRADED -> overwrite caps only (0 state_changed)
  STOPPING/STOPPED/FAILED/PERMANENTLY_FAILED -> InvalidTransitionError

deregister() state path (sub-D9, uses the new REGISTERED->STOPPING edge):
  STOPPING               -> STOPPED (1 state_changed)
  REGISTERED/HEALTHY/DEGRADED -> STOPPING -> STOPPED (2 state_changed)
  STOPPED                -> idempotent (delete entry if present)
  FAILED/PERMANENTLY_FAILED -> delete entry, no transition
  In every case: delete the entry and emit module.deregistered (if present).
"""

from asyncio import QueueEmpty

import pytest
from core.broker import Event, EventBroker, Subscription
from core.config import CoreConfig
from core.lifecycle import InvalidTransitionError, Lifecycle, ModuleState
from core.registry import ModuleEntry, ModuleNotRegisteredError, Registry
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# Test helpers — deterministic clock, wired setup, event drain
# ---------------------------------------------------------------------------


class FakeClock:
    """Monotonic clock advanced by hand — no time.sleep anywhere."""

    def __init__(self, start: float = 1000.0) -> None:
        self._t = start

    def now(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self._t += seconds


def _make_setup() -> tuple[Registry, Lifecycle, EventBroker, FakeClock]:
    """Build a Registry wired to a real Lifecycle + in-memory broker."""
    config = CoreConfig.model_validate({})
    broker = EventBroker()
    clock = FakeClock()
    lifecycle = Lifecycle(config, broker, clock=clock.now)
    registry = Registry(lifecycle, broker)
    return registry, lifecycle, broker, clock


def _drain(sub: Subscription) -> list[Event]:
    """Pull every buffered event off a subscription."""
    out: list[Event] = []
    while True:
        try:
            out.append(sub.get_nowait())
        except QueueEmpty:
            break
    return out


# ---------------------------------------------------------------------------
# ModuleEntry — frozen capability record
# ---------------------------------------------------------------------------


class TestModuleEntry:
    """ModuleEntry is a frozen BaseModel that coerces its collection fields."""

    def test_stores_version(self) -> None:
        entry = ModuleEntry(version="1.0", methods=[], events=[])
        assert entry.version == "1.0"

    def test_methods_coerced_to_frozenset(self) -> None:
        entry = ModuleEntry(version="1.0", methods=["a.b"], events=[])
        assert entry.methods == frozenset({"a.b"})

    def test_events_coerced_to_frozenset(self) -> None:
        entry = ModuleEntry(version="1.0", methods=[], events=["a.x"])
        assert entry.events == frozenset({"a.x"})

    def test_depends_on_coerced_to_tuple(self) -> None:
        entry = ModuleEntry(version="1.0", methods=[], events=[], depends_on=["dep"])
        assert entry.depends_on == ("dep",)

    def test_depends_on_defaults_empty(self) -> None:
        entry = ModuleEntry(version="1.0", methods=[], events=[])
        assert entry.depends_on == ()

    def test_methods_deduplicated(self) -> None:
        entry = ModuleEntry(version="1.0", methods=["a", "a"], events=[])
        assert entry.methods == frozenset({"a"})

    def test_entry_is_frozen(self) -> None:
        entry = ModuleEntry(version="1.0", methods=[], events=[])
        with pytest.raises(ValidationError):
            entry.version = "2.0"


# ---------------------------------------------------------------------------
# register() — the four state-path scenarios (sub-D8)
# ---------------------------------------------------------------------------


class TestRegister:
    """register() drives the lifecycle FSM per the module's current state."""

    def test_untracked_drives_to_registered(self) -> None:
        registry, lifecycle, _broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["vault.unlock"], ["vault.unlocked"])
        assert lifecycle.state_of("vault") == ModuleState.REGISTERED

    def test_untracked_emits_two_state_changes(self) -> None:
        registry, _lifecycle, broker, _clock = _make_setup()
        sub = broker.subscribe(["module.state_changed"])
        registry.register("vault", "1.0", ["m"], [])
        states = [e.payload["to"] for e in _drain(sub)]
        assert states == [ModuleState.STARTING, ModuleState.REGISTERED]

    def test_untracked_makes_module_registered(self) -> None:
        registry, _lifecycle, _broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["m"], [])
        assert registry.is_registered("vault")

    def test_from_starting_single_transition(self) -> None:
        registry, lifecycle, broker, _clock = _make_setup()
        lifecycle.track("vault")
        lifecycle.transition("vault", ModuleState.STARTING)
        sub = broker.subscribe(["module.state_changed"])
        registry.register("vault", "1.0", ["m"], [])
        states = [e.payload["to"] for e in _drain(sub)]
        assert states == [ModuleState.REGISTERED]

    def test_reregister_overwrites_version_no_transition(self) -> None:
        registry, _lifecycle, broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["m"], [])
        sub = broker.subscribe(["module.state_changed"])
        registry.register("vault", "2.0", ["m", "m2"], [])
        assert _drain(sub) == []
        assert registry.get("vault").version == "2.0"

    def test_register_while_healthy_no_transition(self) -> None:
        registry, lifecycle, broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["m"], [])
        lifecycle.transition("vault", ModuleState.HEALTHY)
        sub = broker.subscribe(["module.state_changed"])
        registry.register("vault", "1.1", ["m"], [])
        assert _drain(sub) == []
        assert lifecycle.state_of("vault") == ModuleState.HEALTHY

    def test_register_failed_module_raises(self) -> None:
        registry, lifecycle, _broker, _clock = _make_setup()
        lifecycle.track("vault")
        lifecycle.transition("vault", ModuleState.STARTING)
        lifecycle.transition("vault", ModuleState.FAILED)
        with pytest.raises(InvalidTransitionError):
            registry.register("vault", "1.0", ["m"], [])

    def test_register_stopped_module_raises(self) -> None:
        registry, lifecycle, _broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["m"], [])
        lifecycle.transition("vault", ModuleState.STOPPING)
        lifecycle.transition("vault", ModuleState.STOPPED)
        with pytest.raises(InvalidTransitionError):
            registry.register("vault", "1.0", ["m"], [])


# ---------------------------------------------------------------------------
# deregister() — the four state-path scenarios (sub-D9)
# ---------------------------------------------------------------------------


class TestDeregister:
    """deregister() stops the module gracefully and removes its entry."""

    def test_from_stopping_single_transition(self) -> None:
        registry, lifecycle, broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["m"], [])
        lifecycle.transition("vault", ModuleState.STOPPING)
        sub = broker.subscribe(["module.state_changed"])
        registry.deregister("vault")
        states = [e.payload["to"] for e in _drain(sub)]
        assert states == [ModuleState.STOPPED]

    def test_from_registered_two_transitions(self) -> None:
        registry, _lifecycle, broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["m"], [])
        sub = broker.subscribe(["module.state_changed"])
        registry.deregister("vault")
        states = [e.payload["to"] for e in _drain(sub)]
        assert states == [ModuleState.STOPPING, ModuleState.STOPPED]

    def test_from_healthy_ends_stopped(self) -> None:
        registry, lifecycle, _broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["m"], [])
        lifecycle.transition("vault", ModuleState.HEALTHY)
        registry.deregister("vault")
        assert lifecycle.state_of("vault") == ModuleState.STOPPED

    def test_from_degraded_ends_stopped(self) -> None:
        registry, lifecycle, _broker, clock = _make_setup()
        registry.register("vault", "1.0", ["m"], [])
        lifecycle.transition("vault", ModuleState.HEALTHY)
        lifecycle.heartbeat("vault")
        clock.advance(20)
        lifecycle.sweep_once()
        assert lifecycle.state_of("vault") == ModuleState.DEGRADED
        registry.deregister("vault")
        assert lifecycle.state_of("vault") == ModuleState.STOPPED

    def test_removes_entry(self) -> None:
        registry, _lifecycle, _broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["m"], [])
        registry.deregister("vault")
        assert not registry.is_registered("vault")

    def test_is_idempotent(self) -> None:
        registry, _lifecycle, broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["m"], [])
        registry.deregister("vault")
        sub = broker.subscribe(["module.deregistered"])
        registry.deregister("vault")  # no entry -> no-op
        assert _drain(sub) == []

    def test_failed_module_no_state_transition(self) -> None:
        registry, lifecycle, broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["m"], [])
        lifecycle.transition("vault", ModuleState.FAILED)
        sub = broker.subscribe(["module.state_changed"])
        registry.deregister("vault")
        assert _drain(sub) == []
        assert lifecycle.state_of("vault") == ModuleState.FAILED

    def test_keeps_lifecycle_record(self) -> None:
        registry, lifecycle, _broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["m"], [])
        registry.deregister("vault")
        # registry entry gone, but lifecycle still knows the module (STOPPED).
        assert lifecycle.state_of("vault") == ModuleState.STOPPED


# ---------------------------------------------------------------------------
# capabilities() — the §6.7 snapshot
# ---------------------------------------------------------------------------


class TestCapabilities:
    """capabilities() returns {module: {version, status, methods, events}}."""

    def test_empty_initially(self) -> None:
        registry, _lifecycle, _broker, _clock = _make_setup()
        assert registry.capabilities() == {}

    def test_contains_registered_module(self) -> None:
        registry, _lifecycle, _broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["m"], [])
        assert "vault" in registry.capabilities()

    def test_includes_version(self) -> None:
        registry, _lifecycle, _broker, _clock = _make_setup()
        registry.register("vault", "0.7.0", ["m"], [])
        assert registry.capabilities()["vault"]["version"] == "0.7.0"

    def test_methods_are_sorted_list(self) -> None:
        registry, _lifecycle, _broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["b.2", "b.1"], [])
        assert registry.capabilities()["vault"]["methods"] == ["b.1", "b.2"]

    def test_includes_events(self) -> None:
        registry, _lifecycle, _broker, _clock = _make_setup()
        registry.register("vault", "1.0", [], ["vault.locked"])
        assert registry.capabilities()["vault"]["events"] == ["vault.locked"]

    def test_status_reflects_lifecycle_state(self) -> None:
        registry, _lifecycle, _broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["m"], [])
        assert registry.capabilities()["vault"]["status"] == ModuleState.REGISTERED

    def test_version_after_reregister(self) -> None:
        registry, _lifecycle, _broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["m"], [])
        registry.register("vault", "2.0", ["m"], [])
        assert registry.capabilities()["vault"]["version"] == "2.0"


# ---------------------------------------------------------------------------
# Capability matching — prefix-split + frozenset membership
# ---------------------------------------------------------------------------


class TestCapabilityMatching:
    """has_method() splits on the first dot and checks the module's method set."""

    def test_true_for_registered_method(self) -> None:
        registry, _lifecycle, _broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["vault.unlock"], [])
        assert registry.has_method("vault.unlock")

    def test_false_when_module_unregistered(self) -> None:
        registry, _lifecycle, _broker, _clock = _make_setup()
        assert not registry.has_method("vault.unlock")

    def test_false_for_unknown_method_of_known_module(self) -> None:
        registry, _lifecycle, _broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["vault.unlock"], [])
        assert not registry.has_method("vault.lock")

    def test_matches_multi_dot_method(self) -> None:
        registry, _lifecycle, _broker, _clock = _make_setup()
        registry.register("oracle", "1.0", ["oracle.anomaly.detected"], [])
        assert registry.has_method("oracle.anomaly.detected")

    def test_method_without_dot_is_false(self) -> None:
        registry, _lifecycle, _broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["vault.unlock"], [])
        assert not registry.has_method("vault")

    def test_method_of_other_module_is_false(self) -> None:
        registry, _lifecycle, _broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["vault.unlock"], [])
        assert not registry.has_method("oracle.classify")


# ---------------------------------------------------------------------------
# Queries — get / is_registered / modules_up / dependency_graph
# ---------------------------------------------------------------------------


class TestQueries:
    """Read-only views over the registry."""

    def test_get_returns_entry(self) -> None:
        registry, _lifecycle, _broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["m"], [])
        assert isinstance(registry.get("vault"), ModuleEntry)

    def test_get_unknown_raises(self) -> None:
        registry, _lifecycle, _broker, _clock = _make_setup()
        with pytest.raises(ModuleNotRegisteredError):
            registry.get("ghost")

    def test_is_registered_true(self) -> None:
        registry, _lifecycle, _broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["m"], [])
        assert registry.is_registered("vault")

    def test_is_registered_false(self) -> None:
        registry, _lifecycle, _broker, _clock = _make_setup()
        assert not registry.is_registered("ghost")

    def test_modules_up_lists_healthy(self) -> None:
        registry, lifecycle, _broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["m"], [])
        lifecycle.transition("vault", ModuleState.HEALTHY)
        assert registry.modules_up() == ["vault"]

    def test_modules_up_excludes_merely_registered(self) -> None:
        registry, _lifecycle, _broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["m"], [])  # REGISTERED, not HEALTHY
        assert "vault" not in registry.modules_up()

    def test_dependency_graph_reports_depends_on(self) -> None:
        registry, _lifecycle, _broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["m"], [], depends_on=["pulse", "tether"])
        assert registry.dependency_graph()["vault"] == ("pulse", "tether")

    def test_dependency_graph_empty_deps(self) -> None:
        registry, _lifecycle, _broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["m"], [])
        assert registry.dependency_graph()["vault"] == ()


# ---------------------------------------------------------------------------
# Events — module.registered / module.deregistered payloads
# ---------------------------------------------------------------------------


class TestEvents:
    """register/deregister publish their own capability-level events."""

    def test_register_emits_module_registered(self) -> None:
        registry, _lifecycle, broker, _clock = _make_setup()
        sub = broker.subscribe(["module.registered"])
        registry.register("vault", "1.0", ["m"], [])
        assert len(_drain(sub)) == 1

    def test_registered_payload_has_module(self) -> None:
        registry, _lifecycle, broker, _clock = _make_setup()
        sub = broker.subscribe(["module.registered"])
        registry.register("vault", "1.0", ["m"], [])
        assert _drain(sub)[0].payload["module"] == "vault"

    def test_registered_payload_has_version(self) -> None:
        registry, _lifecycle, broker, _clock = _make_setup()
        sub = broker.subscribe(["module.registered"])
        registry.register("vault", "0.7.0", ["m"], [])
        assert _drain(sub)[0].payload["version"] == "0.7.0"

    def test_registered_payload_has_methods(self) -> None:
        registry, _lifecycle, broker, _clock = _make_setup()
        sub = broker.subscribe(["module.registered"])
        registry.register("vault", "1.0", ["vault.unlock"], [])
        assert _drain(sub)[0].payload["methods"] == ["vault.unlock"]

    def test_registered_payload_has_depends_on(self) -> None:
        registry, _lifecycle, broker, _clock = _make_setup()
        sub = broker.subscribe(["module.registered"])
        registry.register("vault", "1.0", ["m"], [], depends_on=["pulse", "tether"])
        assert _drain(sub)[0].payload["depends_on"] == ["pulse", "tether"]

    def test_deregister_emits_module_deregistered(self) -> None:
        registry, _lifecycle, broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["m"], [])
        sub = broker.subscribe(["module.deregistered"])
        registry.deregister("vault")
        assert len(_drain(sub)) == 1

    def test_deregistered_payload_has_module(self) -> None:
        registry, _lifecycle, broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["m"], [])
        sub = broker.subscribe(["module.deregistered"])
        registry.deregister("vault")
        assert _drain(sub)[0].payload["module"] == "vault"


# ---------------------------------------------------------------------------
# Lifecycle integration — state delegation, transition driving
# ---------------------------------------------------------------------------


class TestLifecycleIntegration:
    """Registry delegates state to Lifecycle and drives its transitions."""

    def test_status_reflects_live_state_without_reregister(self) -> None:
        registry, lifecycle, _broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["m"], [])
        lifecycle.transition("vault", ModuleState.HEALTHY)
        assert registry.capabilities()["vault"]["status"] == ModuleState.HEALTHY

    def test_status_reflects_degraded_after_sweep(self) -> None:
        registry, lifecycle, _broker, clock = _make_setup()
        registry.register("vault", "1.0", ["m"], [])
        lifecycle.transition("vault", ModuleState.HEALTHY)
        lifecycle.heartbeat("vault")
        clock.advance(20)
        lifecycle.sweep_once()
        assert registry.capabilities()["vault"]["status"] == ModuleState.DEGRADED

    def test_register_drives_lifecycle_to_registered(self) -> None:
        registry, lifecycle, _broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["m"], [])
        assert lifecycle.state_of("vault") == ModuleState.REGISTERED

    def test_deregister_drives_lifecycle_to_stopped(self) -> None:
        registry, lifecycle, _broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["m"], [])
        registry.deregister("vault")
        assert lifecycle.state_of("vault") == ModuleState.STOPPED


# ---------------------------------------------------------------------------
# Edge cases — unicode, empty, tuple coercion, frozen
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Boundary conditions that often hide bugs."""

    def test_unicode_module_name(self) -> None:
        registry, _lifecycle, _broker, _clock = _make_setup()
        registry.register("сховище", "1.0", ["сховище.відкрити"], [])
        assert registry.is_registered("сховище")

    def test_register_empty_name_raises(self) -> None:
        registry, _lifecycle, _broker, _clock = _make_setup()
        with pytest.raises(ValueError, match="name"):
            registry.register("", "1.0", [], [])

    def test_depends_on_stored_as_tuple(self) -> None:
        registry, _lifecycle, _broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["m"], [], depends_on=["a", "b"])
        assert registry.get("vault").depends_on == ("a", "b")

    def test_stored_entry_is_frozen(self) -> None:
        registry, _lifecycle, _broker, _clock = _make_setup()
        registry.register("vault", "1.0", ["m"], [])
        entry = registry.get("vault")
        with pytest.raises(ValidationError):
            entry.version = "2.0"

    def test_empty_methods_allowed(self) -> None:
        registry, _lifecycle, _broker, _clock = _make_setup()
        registry.register("vault", "1.0", [], [])
        assert registry.get("vault").methods == frozenset()
