"""RED contract for the module supervisor (SV-2). Fails against the NotImplementedError
stub; green once topological_waves + Supervisor.up/down land.

Unit-level (default suite, no processes): the wave maths is pure, and Supervisor is driven
with fake spawn / is_registered to pin the launch ORDER and the no-hang timeout behaviour.
"""

import pytest
from core.supervisor import CHIMERA_MODULES, ModuleSpec, Supervisor, topological_waves


def test_chimera_modules_covers_all_eight_organs():
    # DP-2: one `chimera up` must raise the whole organism, not just echo+purge.
    names = {s.name for s in CHIMERA_MODULES}
    assert names == {"chaff", "echo", "oracle", "mirror", "pulse", "vault", "tether", "purge"}
    assert {s.name for s in CHIMERA_MODULES if s.python} == {"oracle", "pulse"}  # rest native
    topological_waves(list(CHIMERA_MODULES))  # still valid waves (no cycle / unknown dep)


def test_tether_is_external_others_not():
    # TETHER runs as its OWN LaunchAgent so it is its own TCC subject (Bluetooth grant binds);
    # the supervisor must NOT spawn it. Every other organ stays supervisor-spawned.
    tether = next(s for s in CHIMERA_MODULES if s.name == "tether")
    assert tether.external is True
    assert all(not s.external for s in CHIMERA_MODULES if s.name != "tether")


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


async def test_up_skips_external_modules():
    # external modules are launched by their own LaunchAgent, not the supervisor — up() must
    # neither spawn them nor mark them failed (they register with core on their own).
    spawned = []

    def spawn(spec):
        spawned.append(spec.name)
        return _FakeProc()

    sup = Supervisor(
        [ModuleSpec("a"), ModuleSpec("t", external=True)],
        spawn=spawn,
        is_registered=lambda n: True,
        wave_timeout=1.0,
    )
    await sup.up()
    assert spawned == ["a"]  # "t" (external) was NOT spawned
    assert sup.failed == set()  # nor marked failed


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


async def test_purge_kill_sigkills_all_live_procs():
    """T0-c emergency choreography: after the grace, SIGKILL every live module proc."""
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
    killed = await sup.purge_kill(grace=0)
    assert set(killed) == {"a", "b"}
    assert all(p.killed for p in procs.values())


async def test_purge_kill_skips_already_dead():
    """A proc that has already exited is not force-killed again."""
    procs = {}

    def spawn(spec):
        procs[spec.name] = _FakeProc()
        return procs[spec.name]

    sup = Supervisor(
        [ModuleSpec("a")], spawn=spawn, is_registered=lambda n: True, wave_timeout=1.0
    )
    await sup.up()
    procs["a"].terminate()  # exits -> poll() == 0 (already dead)
    killed = await sup.purge_kill(grace=0)
    assert killed == []
    assert not procs["a"].killed
