"""PULSE idle tracker — group-B's live idle producer (§5.5 / spec §3 group B, PD-idle-1).

temporal_signal's "idle" sub-signal is hours since the last meaningful idle gap ended —
how long the operator has worked without a break (more continuous work = more fatigue).
This derives that timestamp from a stream of system-idle readings: when idle crosses
ABOVE the gap threshold the operator is on a break; when it falls back BELOW (they return
to the keyboard) the gap has just ended -> stamp `last_idle_end`.

Pure + hermetic: idle seconds and `now` are fed in. The real reading (macOS
`ioreg -c IOHIDSystem` HIDIdleTime) is a manual-tier seam wired in the daemon, not here.
"""

from __future__ import annotations

IDLE_GAP_THRESHOLD_S = 300.0  # >= 5 min without input = a meaningful break (PT-idle-1)


class IdleTracker:
    """Tracks when the last meaningful idle gap ended, from system-idle readings."""

    def __init__(self) -> None:
        self._in_gap = False
        self._last_idle_end: str | None = None

    @property
    def last_idle_end(self) -> str | None:
        """ISO timestamp of the end of the most recent idle gap; None until one ends."""
        return self._last_idle_end

    def observe(self, now: str, idle_seconds: float) -> None:
        """Feed one system-idle reading. Detects the END of a meaningful idle gap: idle
        rising past the threshold opens a gap; idle falling back below it closes the gap
        (the operator returned) and stamps `last_idle_end = now`."""
        if idle_seconds >= IDLE_GAP_THRESHOLD_S:
            self._in_gap = True
        elif self._in_gap:
            self._in_gap = False
            self._last_idle_end = now
