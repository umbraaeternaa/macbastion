"""RED contract for the module supervisor (SV-2). Fails against the NotImplementedError
stub; green once topological_waves + Supervisor.up/down land.

Unit-level (default suite, no processes): the wave maths is pure, and Supervisor is driven
with fake spawn / is_registered to pin the launch ORDER and the no-hang timeout behaviour.
"""

import pytest
from core.supervisor import ModuleSpec, Supervisor, topological_waves


def _names(waves):
    return [sorted(s.name for s in wave) for wave in waves]


def test_waves_independent():
    assert _names(topological_waves([ModuleSpec("a"), ModuleSpec("b")])) == [["a", "b"]]


def test_waves_linear():
    specs = [ModuleSpec("b", ("a",)), ModuleSpec("a")]
    assert _names(topological_waves(specs)) == [["a"], ["b"]]


def test_waves_diamond():
    specs = [
        ModuleSpec("a"),
        ModuleSpec("b", ("a",)),
        ModuleSpec("c", ("a",)),
        ModuleSpec("d", ("b", "c")),
    ]
    assert _names(topological_waves(specs)) == [["a"], ["b", "c"], ["d"]]


def test_waves_cycle_rejected():
    specs = [ModuleSpec("a", ("b",)), ModuleSpec("b", ("a",))]
    with pytest.raises(ValueError):
        topological_waves(specs)


def test_waves_unknown_dependency_rejected():
    with pytest.raises(ValueError):
        topological_waves([ModuleSpec("a", ("ghost",))])


class _FakeProc:
    def __init__(self, exits_on_terminate=True):
        self.terminated = False
        self.killed = False
        self._exits = exits_on_terminate

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True

    def poll(self):
        if self.killed:
            return -9
        if self.terminated and self._exits:
            return 0
        return None  # still running


async def test_up_spawns_in_wave_order():
    spawned = []
    registered = set()

    def spawn(spec):
        spawned.append(spec.name)
        registered.add(spec.name)  # registers immediately
        return _FakeProc()

    sup = Supervisor(
        [ModuleSpec("b", ("a",)), ModuleSpec("a")],
        spawn=spawn,
        is_registered=lambda n: n in registered,
        wave_timeout=1.0,
    )
    await sup.up()
    assert spawned == ["a", "b"]  # wave 0 (a) before wave 1 (b)
    assert sup.failed == set()


async def test_up_timeout_does_not_hang():
    def spawn(spec):
        return _FakeProc()

    sup = Supervisor(
        [ModuleSpec("a")], spawn=spawn, is_registered=lambda n: False, wave_timeout=0.2
    )
    await sup.up()  # 'a' never registers -> returns, marks it failed
    assert "a" in sup.failed


async def test_down_terminates_all():
    procs = {}

    def spawn(spec):
        procs[spec.name] = _FakeProc()
        return procs[spec.name]

    sup = Supervisor(
        [ModuleSpec("a"), ModuleSpec("b")],
        spawn=spawn,
        is_registered=lambda n: True,
        wave_timeout=1.0,
    )
    await sup.up()
    await sup.down()
    assert all(p.terminated for p in procs.values())


async def test_down_graceful_then_force():
    procs = {"a": _FakeProc(exits_on_terminate=True), "b": _FakeProc(exits_on_terminate=False)}

    def spawn(spec):
        return procs[spec.name]

    sup = Supervisor(
        [ModuleSpec("a"), ModuleSpec("b")],
        spawn=spawn,
        is_registered=lambda n: True,
        shutdown_grace=0.2,
    )
    await sup.up()
    await sup.down()
    # 'a' exits on SIGTERM -> not force-killed
    assert procs["a"].terminated and not procs["a"].killed
    # 'b' ignores SIGTERM (hung) -> force-killed after the grace window
    assert procs["b"].terminated and procs["b"].killed
