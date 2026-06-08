"""PULSE temporal signal — group B (§5.5 / spec §3 group B), pure & hermetic.

Computes ONE fatigue value in [0,1] from three time-based sub-signals: hour-of-day
(chronotype-weighted), time since the last meaningful idle gap, and total session
duration. Feeds assess(temporal=...). All inputs are injected as ISO strings — no
clock / kqueue inside (hermetic, deterministic).

Locked numbers (PT-1…6): weights hour 0.5 / idle 0.25 / session 0.25; an hour-of-day
curve (low midday, peak ~3am); night_owl x0.4 on night hours; idle = hours/6 clamped;
session = hours/12 clamped. Fail-safe (§8, PULSE fail-open): a missing/None input
contributes 0 (LESS fatigue), never inflates — a broken time sensor must not lock the
operator out. The exact curve/scales are pinned here (spec disambiguation, §9 chronotype
auto-detection deferred — chronotype is an input).
"""

from __future__ import annotations

from datetime import datetime

CHRONOTYPES = ("typical", "night_owl")

# Hour-of-day fatigue base (index = hour 0..23): low midday, peak 3am.
_HOUR_CURVE = [
    0.70, 0.80, 0.90, 1.00, 0.95, 0.80, 0.60, 0.40,  # 00..07
    0.20, 0.10, 0.05, 0.05, 0.10, 0.10, 0.05, 0.10,  # 08..15
    0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50, 0.60,  # 16..23
]
_NIGHT_HOURS = {22, 23, 0, 1, 2, 3, 4, 5, 6}
_NIGHT_OWL_FACTOR = 0.4
_IDLE_FULL_H = 6.0
_SESSION_FULL_H = 12.0
W_HOUR, W_IDLE, W_SESSION = 0.5, 0.25, 0.25


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _hours_between(now: str, earlier: str | None) -> float:
    """Hours from `earlier` to `now`; 0.0 if earlier is None (fail-open)."""
    if earlier is None:
        return 0.0
    delta = datetime.fromisoformat(now) - datetime.fromisoformat(earlier)
    return delta.total_seconds() / 3600.0


def temporal_signal(
    now: str,
    session_start: str | None = None,
    last_idle_end: str | None = None,
    chronotype: str = "typical",
) -> float:
    """Group-B temporal fatigue in [0,1]."""
    hour = datetime.fromisoformat(now).hour
    hour_w = _HOUR_CURVE[hour]
    if chronotype == "night_owl" and hour in _NIGHT_HOURS:
        hour_w *= _NIGHT_OWL_FACTOR
    idle = _clamp01(_hours_between(now, last_idle_end) / _IDLE_FULL_H)
    session = _clamp01(_hours_between(now, session_start) / _SESSION_FULL_H)
    return _clamp01(W_HOUR * hour_w + W_IDLE * idle + W_SESSION * session)
