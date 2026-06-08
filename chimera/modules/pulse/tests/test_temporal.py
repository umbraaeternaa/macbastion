"""PULSE temporal signal tests — group B (§5.5 / spec §3 group B).

Hermetic: all times injected as ISO strings; pinned weights/curve. RED — temporal_signal
raises NotImplementedError until GREEN. Encodes the locked numbers:
weights hour 0.5 / idle 0.25 / session 0.25; hour 3->1.0, 14->0.05; night_owl x0.4 on
night hours; idle = hours/6 clamped; session = hours/12 clamped; missing input -> 0.
"""

from datetime import datetime, timedelta

import pytest
from pulse.temporal import temporal_signal

W_HOUR, W_IDLE, W_SESSION = 0.5, 0.25, 0.25


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _at(hour: int) -> datetime:
    return datetime(2026, 6, 12, hour, 0, 0)


def test_midday_typical_fresh():
    now = _at(14)  # hour weight 0.05; idle/session fresh -> 0
    r = temporal_signal(_iso(now), session_start=_iso(now), last_idle_end=_iso(now))
    assert r == pytest.approx(W_HOUR * 0.05)


def test_3am_typical_fresh():
    now = _at(3)  # hour weight 1.0 (peak)
    r = temporal_signal(_iso(now), session_start=_iso(now), last_idle_end=_iso(now))
    assert r == pytest.approx(W_HOUR * 1.0)


def test_night_owl_dampens_3am():
    now = _at(3)  # night hour x0.4 -> 0.4
    r = temporal_signal(
        _iso(now), session_start=_iso(now), last_idle_end=_iso(now), chronotype="night_owl"
    )
    assert r == pytest.approx(W_HOUR * 0.4)


def test_idle_six_hours_maxes():
    now = _at(14)
    idle = now - timedelta(hours=6)  # 6/6 = 1.0
    r = temporal_signal(_iso(now), session_start=_iso(now), last_idle_end=_iso(idle))
    assert r == pytest.approx(W_HOUR * 0.05 + W_IDLE * 1.0)


def test_idle_partial():
    now = _at(14)
    idle = now - timedelta(hours=3)  # 3/6 = 0.5
    r = temporal_signal(_iso(now), session_start=_iso(now), last_idle_end=_iso(idle))
    assert r == pytest.approx(W_HOUR * 0.05 + W_IDLE * 0.5)


def test_session_twelve_hours_maxes():
    now = _at(14)
    start = now - timedelta(hours=12)  # 12/12 = 1.0
    r = temporal_signal(_iso(now), session_start=_iso(start), last_idle_end=_iso(now))
    assert r == pytest.approx(W_HOUR * 0.05 + W_SESSION * 1.0)


def test_failsafe_missing_inputs_contribute_zero():
    now = _at(14)
    r = temporal_signal(_iso(now))  # session_start / last_idle_end default None -> 0
    assert r == pytest.approx(W_HOUR * 0.05)


def test_clamped_to_one():
    now = _at(3)  # hour 1.0
    idle = now - timedelta(hours=6)  # idle 1.0
    start = now - timedelta(hours=12)  # session 1.0
    r = temporal_signal(_iso(now), session_start=_iso(start), last_idle_end=_iso(idle))
    assert r == pytest.approx(1.0)  # 0.5 + 0.25 + 0.25, clamped


def test_unknown_chronotype_defaults_typical():
    now = _at(3)
    r = temporal_signal(
        _iso(now), session_start=_iso(now), last_idle_end=_iso(now), chronotype="weird"
    )
    assert r == pytest.approx(W_HOUR * 1.0)


def test_always_in_range():
    for h in range(24):
        now = _at(h)
        r = temporal_signal(_iso(now), session_start=_iso(now), last_idle_end=_iso(now))
        assert 0.0 <= r <= 1.0
