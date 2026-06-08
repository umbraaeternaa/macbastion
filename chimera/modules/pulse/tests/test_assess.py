"""PULSE assessment tests (§5.5, slice 3 / WS-1…WS-7).

Hermetic: a real file-based BaselineStore under tmp_path seeded with synthetic
buckets; `now` injected as an ISO string. GREEN — assess() is implemented; the 10
assertions are unchanged from RED. assess() is the only thing under test; the store
is real (already GREEN).
"""

from datetime import datetime, timedelta

import pytest
from pulse.assess import assess
from pulse.baseline import BaselineStore

NOW = datetime(2026, 6, 20, 12, 0, 0)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _seed(store: BaselineStore, values: dict[str, float], days: int) -> None:
    """One non-gated bucket per distinct day for `days` days, all in [NOW-14d, NOW).
    Identical values -> the median of each signal equals that value."""
    for d in range(1, days + 1):
        store.record_bucket(ts=_iso(NOW - timedelta(days=d)), signals=values, gated=False)


@pytest.fixture
def store(tmp_path):
    db = tmp_path / "pulse" / "baseline.db"
    key = tmp_path / "pulse" / "baseline.key"
    return BaselineStore(db, key)


def test_group_a_mean_only(store):
    _seed(store, {"typing_speed": 100.0, "error_rate": 10.0, "mouse_ineff": 1.0}, 14)
    # deltas: (100-50)/100=.5 ; (15-10)/10=.5 ; (1.5-1)/1=.5 ; mean=.5 ; only A present
    score, mode = assess(
        store, _iso(NOW),
        group_a={"typing_speed": 50.0, "error_rate": 15.0, "mouse_ineff": 1.5},
    )
    assert score == pytest.approx(0.5)
    assert mode == "caution"


def test_typing_speed_fast_is_zero(store):
    _seed(store, {"typing_speed": 100.0}, 14)
    score, mode = assess(store, _iso(NOW), group_a={"typing_speed": 150.0})  # faster
    assert score == pytest.approx(0.0)
    assert mode == "normal"


def test_error_rate_high_is_fatigue(store):
    _seed(store, {"error_rate": 10.0}, 14)
    score, mode = assess(store, _iso(NOW), group_a={"error_rate": 20.0})  # (20-10)/10=1
    assert score == pytest.approx(1.0)
    assert mode == "exhausted"


def test_signal_without_baseline_skipped(store):
    _seed(store, {"typing_speed": 100.0}, 14)  # only typing_speed has a baseline
    # mouse_ineff has no baseline -> skipped; input_delta = mean([.5]) = .5
    score, _ = assess(
        store, _iso(NOW), group_a={"typing_speed": 50.0, "mouse_ineff": 99.0}
    )
    assert score == pytest.approx(0.5)


def test_group_a_absent_temporal_drives(store):
    _seed(store, {"typing_speed": 100.0}, 14)  # seeded only for baseline_ready
    score, mode = assess(store, _iso(NOW), group_a=None, temporal=0.8)
    assert score == pytest.approx(0.8)
    assert mode == "tired"


def test_drift_group_c(store):
    _seed(store, {"typing_speed": 100.0}, 14)
    score, mode = assess(store, _iso(NOW), group_a=None, temporal=None, drift=0.95)
    assert score == pytest.approx(0.95)
    assert mode == "exhausted"


def test_all_absent_failsafe_normal(store):
    _seed(store, {"typing_speed": 100.0}, 14)
    score, mode = assess(store, _iso(NOW), group_a=None, temporal=None, drift=None)
    assert score == pytest.approx(0.0)
    assert mode == "normal"


def test_baseline_not_ready_forces_normal(store):
    _seed(store, {"typing_speed": 100.0}, 13)  # 13 distinct days -> not ready
    score, mode = assess(store, _iso(NOW), group_a={"typing_speed": 50.0})
    assert score == pytest.approx(0.5)  # score still computed
    assert mode == "normal"  # but mode frozen during calibration


def test_renorm_group_a_plus_temporal(store):
    _seed(store, {"typing_speed": 100.0}, 14)
    # typing_speed current 0 -> delta (100-0)/100 = 1.0 ; temporal = 0.0
    # present weights w_a=.55, w_b=.30 -> score = (.55/.85)*1.0 + (.30/.85)*0.0
    score, mode = assess(store, _iso(NOW), group_a={"typing_speed": 0.0}, temporal=0.0)
    assert score == pytest.approx(0.55 / 0.85)
    assert mode == "caution"


def test_gated_buckets_excluded(store):
    _seed(store, {"typing_speed": 100.0}, 14)
    # gated outliers that would drag the median down if counted
    for d in range(1, 15):
        store.record_bucket(
            ts=_iso(NOW - timedelta(days=d, hours=1)),
            signals={"typing_speed": 10.0},
            gated=True,
        )
    # baseline stays 100 (gated excluded) -> delta (100-50)/100 = .5
    score, _ = assess(store, _iso(NOW), group_a={"typing_speed": 50.0})
    assert score == pytest.approx(0.5)
