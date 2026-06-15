"""RED contract for the supervisor autonomy link (SV-5'b). Fails against the
NotImplementedError stubs; green once handle_failure / on_state_changed land.

Unit-level (default): a real core.lifecycle (the §7.5 decision owner) + a fake spawn.
The supervisor delegates the restart DECISION to lifecycle and only performs the process
ACTION (re-spawn) when lifecycle says STARTING.
"""

from core.broker import EventBroker
from core.config import CoreConfig
from core.lifecycle import Lifecycle, ModuleState
from core.supervisor import ModuleSpec, Supervisor


def _failed_lifecycle(name, socket_dir, *, restart_max=5):
    cfg = CoreConfig.model_validate(
        {"socket_dir": str(socket_dir), "restart_max_per_hour": restart_max}
    )
    lc = Lifecycle(cfg, EventBroker(), clock=lambda: 0.0)
    lc.track(name)
    lc.transition(name, ModuleState.STARTING)
    lc.transition(name, ModuleState.REGISTERED)
    lc.transition(name, ModuleState.FAILED)
    return lc


class _FakeProc:
    def terminate(self):  # pragma: no cover
        ...


def _sup():
    spawned = []

    def spawn(spec):
        spawned.append(spec.name)
        return _FakeProc()

    return Supervisor([ModuleSpec("a")], spawn=spawn, is_registered=lambda n: True), spawned


def test_handle_failure_respawns_within_budget(tmp_path):
    lc = _failed_lifecycle("a", tmp_path)
    sup, spawned = _sup()
    assert sup.handle_failure("a", lc) is True
    assert lc.state_of("a") == ModuleState.STARTING
    assert spawned == ["a"]


def test_handle_failure_gives_up_over_budget(tmp_path):
    lc = _failed_lifecycle("a", tmp_path, restart_max=1)
    sup, spawned = _sup()
    assert sup.handle_failure("a", lc) is True  # 1st restart -> STARTING + respawn
    lc.transition("a", ModuleState.FAILED)  # it crashes again
    assert sup.handle_failure("a", lc) is False  # over budget -> permanently failed
    assert lc.state_of("a") == ModuleState.PERMANENTLY_FAILED
    assert spawned == ["a"]  # only the first respawn happened


def test_handle_failure_unknown_module_ignored(tmp_path):
    lc = _failed_lifecycle("a", tmp_path)
    sup, spawned = _sup()
    assert sup.handle_failure("ghost", lc) is False
    assert spawned == []


def test_handle_failure_skips_external(tmp_path):
    # an external module (its own LaunchAgent) is restarted by launchd KeepAlive, NOT by us —
    # the supervisor must not respawn it on FAILED (else it duplicates the launchd-run daemon).
    lc = _failed_lifecycle("t", tmp_path)
    spawned = []

    def spawn(spec):
        spawned.append(spec.name)
        return _FakeProc()

    sup = Supervisor([ModuleSpec("t", external=True)], spawn=spawn, is_registered=lambda n: True)
    assert sup.handle_failure("t", lc) is False
    assert spawned == []


def test_on_state_changed_only_acts_on_failed(tmp_path):
    lc = _failed_lifecycle("a", tmp_path)
    sup, spawned = _sup()
    ignored = sup.on_state_changed(
        {"module": "a", "from": ModuleState.HEALTHY, "to": ModuleState.DEGRADED}, lc
    )
    assert ignored is False
    assert spawned == []
    acted = sup.on_state_changed(
        {"module": "a", "from": ModuleState.DEGRADED, "to": ModuleState.FAILED}, lc
    )
    assert acted is True
    assert spawned == ["a"]
