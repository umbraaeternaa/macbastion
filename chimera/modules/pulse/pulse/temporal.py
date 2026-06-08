"""PULSE temporal signal — group B (§5.5 / spec §3 group B), pure & hermetic.

Computes ONE fatigue value in [0,1] from three time-based sub-signals: hour-of-day
(chronotype-weighted), time since the last meaningful idle gap, and total session
duration. Feeds assess(temporal=...). All inputs are injected as ISO strings — no
clock / kqueue inside (hermetic, deterministic).

RED stub: the public surface is fixed; behaviour raises NotImplementedError so the
failing tests are real (an honest empty stub, never a pretending one — MANIFESTO §4).

Fail-safe (§8, PULSE fail-open): a missing/None input contributes 0 (LESS fatigue),
never inflates — a broken/absent time sensor must not lock the operator out.
"""

from __future__ import annotations

CHRONOTYPES = ("typical", "night_owl")


def temporal_signal(
    now: str,
    session_start: str | None = None,
    last_idle_end: str | None = None,
    chronotype: str = "typical",
) -> float:
    """Group-B temporal fatigue in [0,1]: weighted sum of the chronotype-weighted
    hour-of-day curve (0.5), hours-since-idle/6 clamped (0.25), and session-hours/12
    clamped (0.25); missing session_start/last_idle_end contribute 0 (fail-open)."""
    raise NotImplementedError
