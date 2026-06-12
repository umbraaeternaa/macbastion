"""PULSE drift tracker — group-C live producer (§5.5 / spec §3 group C, PD-C-1).

ORACLE emits oracle.anomaly.detected {score} when an anomaly crosses the threshold. This
holds that score as the group-C "behavioral drift" fatigue signal for a 5-minute window
(spec §3: a flagged anomaly factors into fatigue within the same 5-min window), then it
decays to absent. Only a meaningful anomaly (score > DRIFT_MIN) counts. Pure + hermetic:
the score and `now` are fed in; assess() consumes drift().
"""

from __future__ import annotations

from datetime import datetime

DRIFT_WINDOW_S = 300.0  # a flagged anomaly factors into fatigue for 5 minutes (spec §3)
DRIFT_MIN = 0.3  # only a meaningful anomaly counts (spec §3 group C)


class DriftTracker:
    """Holds the latest ORACLE anomaly score as a time-windowed drift signal."""

    def __init__(self) -> None:
        self._ts: str | None = None
        self._score = 0.0

    def observe(self, now: str, score: float) -> None:
        """Record an anomaly score from an oracle.anomaly.detected event."""
        self._ts = now
        self._score = score

    def drift(self, now: str) -> float | None:
        """The group-C drift signal: the last anomaly's score if it is meaningful (>
        DRIFT_MIN) and still within DRIFT_WINDOW_S, else None (ORACLE quiet or aged out)."""
        if self._ts is None or self._score <= DRIFT_MIN:
            return None
        elapsed = (
            datetime.fromisoformat(now) - datetime.fromisoformat(self._ts)
        ).total_seconds()
        return self._score if elapsed < DRIFT_WINDOW_S else None
