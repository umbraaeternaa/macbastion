"""PULSE group-A mapper — MIRROR per-minute aggregates -> the three fatigue readings
assess() consumes (§5.5 / spec §3 group A, PD-A-1).

MIRROR exposes only aggregate counters (privacy §8 — never raw keystrokes/coordinates):
chars typed, deletes, and the mouse path-length-vs-straight-line ratio. This maps them
onto the group-A signals (typing_speed, error_rate, mouse_ineff). A signal with no data
this minute is ABSENT (not 0): a pause is not gradely-slow typing, and no mouse movement
is not a perfectly-efficient path — assess() skips absent signals (WS-4), so a quiet
minute can't masquerade as peak fatigue.
"""

from __future__ import annotations


def input_signals(
    chars: int, deletes: int, mouse_path_ratio: float | None
) -> dict[str, float]:
    """One minute of MIRROR aggregates -> the present group-A readings (absent omitted)."""
    out: dict[str, float] = {}
    if chars > 0:
        out["typing_speed"] = float(chars)
        out["error_rate"] = deletes / chars
    if mouse_path_ratio is not None:
        out["mouse_ineff"] = float(mouse_path_ratio)
    return out
