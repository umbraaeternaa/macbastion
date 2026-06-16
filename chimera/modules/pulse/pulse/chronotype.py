"""PULSE chronotype auto-detection — §9 (was deferred; now learned, not an input).

Pure & hermetic: decide the operator's chronotype from a 24-slot hour-of-activity
histogram (one count per ACTIVE minute, bucketed by local hour). No clock, no I/O — the
caller owns observation + persistence; this module is only the decision, so it is unit-
tested directly (mirrors temporal.py / gate.py).

Locked numbers (CT-1…3): NIGHT_HOURS = {22,23,0..6} (shared with temporal's night curve);
MIN_SAMPLES = 600 active minutes (~10 h of presence) before any verdict; a night owl is
declared only when the night share of activity reaches NIGHT_THRESHOLD = 0.30 (inclusive).
Fail-safe (§8, PULSE fail-open): too little / missing / malformed data -> "typical" — never
invent a night owl, so a cold or broken sensor never silently dampens fatigue at night.
"""

from __future__ import annotations

NIGHT_HOURS = frozenset({22, 23, 0, 1, 2, 3, 4, 5, 6})
MIN_SAMPLES = 600
NIGHT_THRESHOLD = 0.30


def empty_histogram() -> list[int]:
    """A fresh 24-slot (hour-of-day) activity histogram, all zero."""
    return [0] * 24


def bump(hist: list[int], hour: int) -> None:
    """Record one active minute at `hour`; out-of-range hours are ignored (§8 — a
    defensive bump must never crash the tick loop). datetime.hour is always 0..23."""
    if 0 <= hour < 24:
        hist[hour] += 1


def classify_chronotype(
    hour_hist: list[int] | None,
    *,
    min_samples: int = MIN_SAMPLES,
    night_threshold: float = NIGHT_THRESHOLD,
) -> str:
    """Classify "typical" vs "night_owl" from the activity histogram (CT-1…3).

    Fail-safe: an empty/None/sub-sample histogram returns "typical"; a night owl needs
    both enough samples AND a night share >= night_threshold.
    """
    if not hour_hist:
        return "typical"
    total = sum(hour_hist)
    if total < min_samples:
        return "typical"
    night = sum(hour_hist[h] for h in NIGHT_HOURS if h < len(hour_hist))
    return "night_owl" if (night / total) >= night_threshold else "typical"
