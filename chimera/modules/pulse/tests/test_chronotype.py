"""PULSE chronotype auto-detection tests — §9 (was deferred; chronotype is now learned).

Hermetic + pure: the classifier reads a 24-slot hour-of-activity histogram and decides
"typical" vs "night_owl"; no clock, no I/O. RED until pulse/chronotype.py lands. Encodes
the locked numbers: NIGHT_HOURS = {22,23,0..6}; MIN_SAMPLES = 600 active minutes;
NIGHT_THRESHOLD = 0.30 night share (>=); fail-safe — too little data -> "typical" (never
invent a night owl, never inflate fatigue dampening on a cold sensor, PULSE fail-open §8).
"""

import pytest
from pulse.chronotype import (
    MIN_SAMPLES,
    NIGHT_HOURS,
    NIGHT_THRESHOLD,
    bump,
    classify_chronotype,
    empty_histogram,
)


def _hist(night: int, day: int) -> list[int]:
    """Build a histogram with `night` counts on a night hour (3am) and `day` on a day hour (14)."""
    h = empty_histogram()
    h[3] = night  # 3am is in NIGHT_HOURS
    h[14] = day  # 2pm is not
    return h


def test_night_hours_are_the_locked_set():
    assert NIGHT_HOURS == frozenset({22, 23, 0, 1, 2, 3, 4, 5, 6})


def test_empty_histogram_is_24_zeros():
    h = empty_histogram()
    assert h == [0] * 24
    assert len(h) == 24


def test_bump_increments_the_hour():
    h = empty_histogram()
    bump(h, 3)
    bump(h, 3)
    bump(h, 14)
    assert h[3] == 2
    assert h[14] == 1
    assert sum(h) == 3


def test_bump_out_of_range_is_a_noop():
    # datetime.hour is always 0..23; a defensive bump never crashes the tick loop (§8).
    h = empty_histogram()
    bump(h, 24)
    bump(h, -1)
    assert sum(h) == 0


def test_insufficient_samples_is_typical():
    # Below MIN_SAMPLES the verdict is "typical" even if every sample is nocturnal.
    h = _hist(night=MIN_SAMPLES - 1, day=0)
    assert classify_chronotype(h) == "typical"


def test_night_heavy_is_night_owl():
    h = _hist(night=300, day=300)  # total 600 == MIN_SAMPLES, night share 0.5 >= 0.30
    assert classify_chronotype(h) == "night_owl"


def test_threshold_boundary_is_inclusive():
    h = _hist(night=300, day=700)  # total 1000, night share exactly 0.30 -> night_owl (>=)
    assert classify_chronotype(h) == "night_owl"


def test_day_heavy_is_typical():
    h = _hist(night=200, day=800)  # total 1000, night share 0.20 < 0.30
    assert classify_chronotype(h) == "typical"


def test_custom_thresholds_respected():
    h = _hist(night=60, day=40)  # total 100, night share 0.60
    assert classify_chronotype(h, min_samples=50, night_threshold=0.50) == "night_owl"
    assert classify_chronotype(h, min_samples=50, night_threshold=0.70) == "typical"
    assert classify_chronotype(h, min_samples=200, night_threshold=0.50) == "typical"  # too few


def test_all_zeros_is_typical():
    assert classify_chronotype(empty_histogram()) == "typical"


def test_none_or_short_hist_is_typical():
    # Fail-safe: malformed/missing histogram never raises, never invents a night owl.
    assert classify_chronotype(None) == "typical"
    assert classify_chronotype([]) == "typical"


def test_default_constants():
    assert MIN_SAMPLES == 600
    assert NIGHT_THRESHOLD == pytest.approx(0.30)
