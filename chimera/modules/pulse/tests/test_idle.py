"""PULSE idle tracker — group-B's live idle producer (PD-idle-1).

temporal_signal's "idle" sub-signal is hours since the last meaningful idle gap ended.
IdleTracker derives that timestamp (`last_idle_end`) from a stream of system-idle
readings. RED until pulse/idle.py lands; pure + hermetic (no clock, no OS)."""

from pulse.idle import IDLE_GAP_THRESHOLD_S, IdleTracker


def test_new_tracker_has_no_idle_end() -> None:
    assert IdleTracker().last_idle_end is None


def test_working_only_never_stamps() -> None:
    t = IdleTracker()
    t.observe("2026-06-12T10:00:00", 5.0)
    t.observe("2026-06-12T10:01:00", 12.0)
    assert t.last_idle_end is None  # never crossed the gap threshold — no break yet


def test_in_gap_not_yet_ended() -> None:
    t = IdleTracker()
    t.observe("2026-06-12T10:00:00", IDLE_GAP_THRESHOLD_S + 60)  # away (on a break)
    assert t.last_idle_end is None  # still idle — the gap hasn't ended


def test_gap_end_stamps_on_return() -> None:
    t = IdleTracker()
    t.observe("2026-06-12T10:00:00", IDLE_GAP_THRESHOLD_S + 60)  # away
    t.observe("2026-06-12T10:06:00", 2.0)                        # returned to the keyboard
    assert t.last_idle_end == "2026-06-12T10:06:00"  # the gap just ended


def test_latest_gap_wins() -> None:
    t = IdleTracker()
    t.observe("2026-06-12T10:00:00", IDLE_GAP_THRESHOLD_S + 1)
    t.observe("2026-06-12T10:06:00", 1.0)  # first gap ends
    t.observe("2026-06-12T12:00:00", IDLE_GAP_THRESHOLD_S + 1)
    t.observe("2026-06-12T12:30:00", 1.0)  # second gap ends
    assert t.last_idle_end == "2026-06-12T12:30:00"  # most recent break wins
