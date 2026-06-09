"""Module registry — capabilities + lifecycle states (§6.7, §7.2).

Core's live directory of every registered module: its advertised version,
methods, events, and declared dependencies (§6.7). The registry does NOT
store a module's state — it composes the Lifecycle FSM and delegates status
to lifecycle.state_of(), so there is exactly one source of truth for state
(§7.2).

Design (operator-approved, pinned by tests/test_registry.py):
- Storage: dict[str, ModuleEntry]; ModuleEntry is frozen. In-RAM only; the
  registry is rebuilt from re-registration after a core restart (§7.8).
- Registration: last-write-wins overwrite, so a module can re-register on
  reconnect (§7.8).
- Capability matching: a namespaced method "vault.unlock" is owned by the
  module before the first dot; membership is an O(1) frozenset check.
- Orchestration: register()/deregister() DRIVE the lifecycle FSM through the
  legal transitions (sub-D8 / sub-D9), then emit a capability-level
  module.registered / module.deregistered event via the injected broker.
- Auth is NOT here: the registry answers "does this method exist" (-31002),
  never "is the caller allowed" (-31007); token checks live in the server.

I3 (fail-closed): modules_up() reports only HEALTHY modules — a DEGRADED
module is not treated as fully up.
"""

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict

from core.broker import Event, EventBroker
from core.lifecycle import InvalidTransitionError, Lifecycle, ModuleState


class ModuleEntry(BaseModel):
    """Immutable capability record for one registered module (§6.7).

    The module name is the registry's dict key, not a field here. List inputs
    for methods/events/depends_on are coerced to frozenset/tuple by pydantic,
    so a stored entry is fully immutable.
    """

    model_config = ConfigDict(frozen=True)

    version: str
    methods: frozenset[str]
    events: frozenset[str]
    depends_on: tuple[str, ...] = ()


class ModuleNotRegisteredError(Exception):
    """Raised when a query references a module absent from the registry.

    Named to avoid colliding with Python's built-in ModuleNotFoundError (the
    import-system error); this is purely about the CHIMERA registry.
    """


class Registry:
    """Live capability registry that composes and drives the Lifecycle FSM."""

    REGISTERED_TOPIC: ClassVar[str] = "module.registered"
    DEREGISTERED_TOPIC: ClassVar[str] = "module.deregistered"
    # The "alive" states. On register() they mean "already up, capability
    # update only"; on deregister() they mean "stop gracefully via STOPPING".
    _LIVE_STATES: ClassVar[frozenset[ModuleState]] = frozenset(
        {ModuleState.REGISTERED, ModuleState.HEALTHY, ModuleState.DEGRADED}
    )

    def __init__(self, lifecycle: Lifecycle, broker: EventBroker) -> None:
        self._lifecycle = lifecycle
        self._broker = broker
        self._entries: dict[str, ModuleEntry] = {}

    # -- registration -----------------------------------------------------

    def register(
        self,
        name: str,
        version: str,
        methods: list[str],
        events: list[str],
        depends_on: list[str] | None = None,
    ) -> None:
        """Register or update a module's capabilities, driving the FSM (sub-D8).

        Untracked -> STARTING -> REGISTERED; STARTING -> REGISTERED; a module
        already REGISTERED/HEALTHY/DEGRADED keeps its state (capability update
        only); any terminal/stopping state raises InvalidTransitionError —
        the registry never resurrects a stopped or failed module.
        """
        self._drive_register(name)
        entry = ModuleEntry(
            version=version,
            methods=frozenset(methods),
            events=frozenset(events),
            depends_on=tuple(depends_on or ()),
        )
        self._entries[name] = entry
        self._emit_registered(name, entry)

    def _drive_register(self, name: str) -> None:
        """Move the module's lifecycle state to REGISTERED per sub-D8."""
        state = self._state_or_none(name)
        if state is None:  # untracked: full startup chain
            self._lifecycle.track(name)
            self._lifecycle.transition(name, ModuleState.STARTING)
            self._lifecycle.transition(name, ModuleState.REGISTERED)
        elif state == ModuleState.STARTING:
            self._lifecycle.transition(name, ModuleState.REGISTERED)
        elif state in self._LIVE_STATES:
            return  # capability update only, no transition
        else:
            raise InvalidTransitionError(
                f"cannot register module {name!r} in state {state}"
            )

    def deregister(self, name: str) -> None:
        """Gracefully stop and remove a module, driving the FSM (sub-D9).

        Idempotent: deregistering an absent module is a silent no-op. Live
        states (REGISTERED/HEALTHY/DEGRADED) walk -> STOPPING -> STOPPED;
        STOPPING walks -> STOPPED; terminal states keep their state. In every
        present case the entry is removed and module.deregistered emitted.
        """
        if not self.is_registered(name):
            return
        state = self._lifecycle.state_of(name)
        if state in self._LIVE_STATES:
            self._lifecycle.transition(name, ModuleState.STOPPING)
            self._lifecycle.transition(name, ModuleState.STOPPED)
        elif state == ModuleState.STOPPING:
            self._lifecycle.transition(name, ModuleState.STOPPED)
        del self._entries[name]
        self._emit_deregistered(name)

    def mark_lost(self, name: str) -> None:
        """An abrupt connection loss (crash, not a graceful deregister): if the module is
        still live, transition it to FAILED so the supervisor can restart it (§7.5). No-op
        if absent or already terminal — a graceful deregister (-> STOPPED) is left alone."""
        if not self.is_registered(name):
            return
        if self._lifecycle.state_of(name) in self._LIVE_STATES:
            self._lifecycle.transition(name, ModuleState.FAILED)

    # -- queries ----------------------------------------------------------

    def get(self, name: str) -> ModuleEntry:
        """Return a module's capability entry. Raises ModuleNotRegisteredError."""
        try:
            return self._entries[name]
        except KeyError as e:
            raise ModuleNotRegisteredError(name) from e

    def is_registered(self, name: str) -> bool:
        return name in self._entries

    def has_method(self, method: str) -> bool:
        """True iff the owning module (prefix before the first dot) advertises it."""
        module, dot, _rest = method.partition(".")
        if not dot:  # no namespace prefix -> not a routable method
            return False
        entry = self._entries.get(module)
        return entry is not None and method in entry.methods

    def modules_up(self) -> list[str]:
        """Names of modules currently HEALTHY (I3: DEGRADED is not 'up')."""
        return sorted(
            name
            for name in self._entries
            if self._lifecycle.state_of(name) == ModuleState.HEALTHY
        )

    def capabilities(self) -> dict[str, dict[str, Any]]:
        """§6.7 snapshot: {module: {version, status, methods, events}}.

        Methods/events are sorted lists (JSON-friendly); status is delegated
        live from the lifecycle FSM, never stored here.
        """
        return {
            name: {
                "version": entry.version,
                "status": self._lifecycle.state_of(name),
                "methods": sorted(entry.methods),
                "events": sorted(entry.events),
            }
            for name, entry in self._entries.items()
        }

    def dependency_graph(self) -> dict[str, tuple[str, ...]]:
        """Raw declared dependencies per module (topo-sort deferred to server)."""
        return {name: entry.depends_on for name, entry in self._entries.items()}

    # -- internals --------------------------------------------------------

    def _state_or_none(self, name: str) -> ModuleState | None:
        """Lifecycle state of a module, or None if it is not tracked."""
        try:
            return self._lifecycle.state_of(name)
        except KeyError:
            return None

    def _emit_registered(self, name: str, entry: ModuleEntry) -> None:
        payload: dict[str, Any] = {
            "module": name,
            "version": entry.version,
            "methods": sorted(entry.methods),
            "events": sorted(entry.events),
            "depends_on": list(entry.depends_on),
        }
        self._broker.publish(Event(topic=self.REGISTERED_TOPIC, payload=payload))

    def _emit_deregistered(self, name: str) -> None:
        payload: dict[str, Any] = {"module": name}
        self._broker.publish(Event(topic=self.DEREGISTERED_TOPIC, payload=payload))
