"""PULSE drift tracker — group-C live producer (PD-C-1).

ORACLE already emits oracle.anomaly.detected {score} when an anomaly crosses the
threshold. DriftTracker holds that score as the group-C drift signal for a 5-minute
window, then it decays to absent. RED until pulse/drift.py lands; pure + hermetic."""

from pulse.drift import DRIFT_MIN, DRIFT_WINDOW_S, DriftTracker


def test_fresh_has_no_drift() -> None:
    assert DriftTracker().drift("2026-06-12T10:00:00") is None


def test_recent_anomaly_is_drift() -> None:
    t = DriftTracker()
    t.observe("2026-06-12T10:00:00", 0.8)
    assert t.drift("2026-06-12T10:02:00") == 0.8  # within the 5-min window


def test_anomaly_decays_after_window() -> None:
    t = DriftTracker()
    t.observe("2026-06-12T10:00:00", 0.8)
    # 6 min later, past DRIFT_WINDOW_S -> the anomaly no longer factors into fatigue
    assert t.drift("2026-06-12T10:06:00") is None


def test_insignificant_anomaly_ignored() -> None:
    t = DriftTracker()
    t.observe("2026-06-12T10:00:00", 0.2)  # <= DRIFT_MIN (0.3) — not meaningful
    assert t.drift("2026-06-12T10:01:00") is None


def test_window_and_min_constants() -> None:
    assert DRIFT_WINDOW_S == 300.0
    assert DRIFT_MIN == 0.3
