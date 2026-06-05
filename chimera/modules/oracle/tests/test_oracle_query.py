"""Unit: TimeMachine — structured time-range queries (#2, TM-1c Layer 1).

Deterministic (no LLM): seed events with known ts, assert exact results.
Against the stub (first_seen/period_summary raise) every assertion fails — RED.
"""

from oracle.baseline import BaselineStore
from oracle.query import TimeMachine


def _store(tmp_path):
    return BaselineStore(tmp_path / "baseline.db", tmp_path / "baseline.key")


def _rec(store, ts, source, etype):
    store.record_event(ts=ts, source=source, event_type=etype, payload={})


async def test_first_seen_returns_earliest(tmp_path):
    store = _store(tmp_path)
    _rec(store, "2026-06-03T10:00:00+00:00", "chaff", "request.sent")
    _rec(store, "2026-06-01T10:00:00+00:00", "chaff", "request.sent")  # earliest
    _rec(store, "2026-06-02T10:00:00+00:00", "chaff", "request.sent")
    result = await TimeMachine(store).first_seen("chaff")
    assert result["source"] == "chaff"
    assert result["first_seen"] == "2026-06-01T10:00:00+00:00"


async def test_first_seen_filters_by_type(tmp_path):
    store = _store(tmp_path)
    _rec(store, "2026-06-01T10:00:00+00:00", "chaff", "request.sent")
    _rec(store, "2026-06-02T10:00:00+00:00", "chaff", "error")
    result = await TimeMachine(store).first_seen("chaff", "error")
    assert result["event_type"] == "error"
    assert result["first_seen"] == "2026-06-02T10:00:00+00:00"


async def test_first_seen_absent_is_none(tmp_path):
    result = await TimeMachine(_store(tmp_path)).first_seen("nope")
    assert result["first_seen"] is None


async def test_period_summary_half_open(tmp_path):
    store = _store(tmp_path)
    _rec(store, "2026-06-01T10:00:00+00:00", "chaff", "request.sent")
    _rec(store, "2026-06-02T10:00:00+00:00", "chaff", "request.sent")
    _rec(store, "2026-06-03T10:00:00+00:00", "mirror", "move")
    # [start, end): includes 06-02, excludes 06-03
    result = await TimeMachine(store).period_summary("2026-06-02", "2026-06-03")
    assert result["start"] == "2026-06-02"
    assert result["end"] == "2026-06-03"
    assert result["total"] == 1
    assert result["by_source"] == {"chaff": 1}
    assert result["by_type"] == {"request.sent": 1}
