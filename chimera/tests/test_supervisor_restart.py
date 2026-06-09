"""RED contract for the restart policy (SV-3, §7.5). Fails against the NotImplementedError
stubs; green once backoff_delay / RestartTracker / Supervisor.restart land.

Fully unit-level (default suite): pure backoff curve + rolling-window budget + a restart
method driven with a fake spawn and injected `now` — no real processes or clocks.
"""

import pytest
from core.supervisor import ModuleSpec, RestartTracker, Supervisor, backoff_delay


def test_backoff_delay_curve():
    assert [backoff_delay(a) for a in (1, 2, 3, 4, 5, 6)] == [1.0, 2.0, 4.0, 8.0, 30.0, 30.0]


def test_tracker_counts_within_window():
    t = RestartTracker(max_restarts=5, window_s=3600.0)
    for n in range(3):
        t.record(now=float(n))
    assert t.attempts(now=10.0) == 3
    assert t.allowed(now=10.0) is True


def test_tracker_prunes_outside_window():
    t = RestartTracker(max_restarts=5, window_s=3600.0)
    t.record(now=0.0)
    assert t.attempts(now=4000.0) == 0  # the 1h window has elapsed


def test_tracker_gives_up_after_max():
    t = RestartTracker(max_restarts=5, window_s=3600.0)
    for n in range(5):
        t.record(now=float(n))
    assert t.allowed(now=10.0) is False


class _FakeProc:
    def terminate(self):  # pragma: no cover - trivial
        ...


def _sup():
    spawned = []

    def spawn(spec):
        spawned.append(spec.name)
        return _FakeProc()

    sup = Supervisor(
        [ModuleSpec("a")], spawn=spawn, is_registered=lambda n: True, max_restarts=5
    )
    return sup, spawned


def test_restart_respawns_with_backoff():
    sup, spawned = _sup()
    delays = [sup.restart("a", now=float(i)) for i in range(5)]
    assert delays == [1.0, 2.0, 4.0, 8.0, 30.0]
    assert spawned == ["a"] * 5


def test_restart_gives_up_after_max():
    sup, spawned = _sup()
    for i in range(5):
        sup.restart("a", now=float(i))
    assert sup.restart("a", now=5.0) is None  # budget exhausted -> permanently failed
    assert "a" in sup.dead
    assert spawned == ["a"] * 5  # the 6th attempt did NOT respawn


def test_restart_unknown_module_rejected():
    sup, _ = _sup()
    with pytest.raises((KeyError, ValueError)):
        sup.restart("ghost", now=0.0)
