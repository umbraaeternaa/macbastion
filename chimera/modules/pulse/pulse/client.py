"""PULSE daemon core client (§5.5, daemon slice / PD-1…PD-9).

Module-only client (PD-1): ONE core.sock connection that registers with core, serves
pulse.* via the 4A router, and heartbeats — mirroring ORACLE's command connection.
PULSE's group-A (MIRROR aggregates) and group-C (ORACLE drift) consumers are gated, so
there is no events.sock consumer this slice.

RED stub: the public surface is fixed; run() raises NotImplementedError so the failing
integration tests are real (an honest empty stub — MANIFESTO §4). In GREEN, pulse.status
composes the live edge (temporal_signal -> assess over the store) — advisory only,
fail-open (mode 'normal' while uncalibrated; §8). Reuses core.envelope + core.errors
only (D1=c; extract a shared pyclient at the 2nd Python module — same TODO as ORACLE).
"""

from __future__ import annotations

from pathlib import Path

from pulse.baseline import BaselineStore
from pulse.scoring import Weights


class PulseClient:
    """PULSE daemon's core client (module role)."""

    MODULE = "pulse"
    VERSION = "0.1.0-alpha"
    METHODS: tuple[str, ...] = (
        "pulse.status",
        "pulse.weights.set",
        "pulse.enable",
        "pulse.disable",
    )
    EVENTS: tuple[str, ...] = ("pulse.mode.changed", "pulse.error")

    def __init__(
        self,
        socket_dir: Path,
        store: BaselineStore,
        *,
        session_start: str | None = None,
        chronotype: str = "typical",
        weights: Weights | None = None,
        heartbeat_interval: float = 2.0,
    ) -> None:
        self._socket_dir = Path(socket_dir)
        self._store = store
        self._session_start = session_start
        self._chronotype = chronotype
        self._weights = weights if weights is not None else Weights()
        self._heartbeat_interval = heartbeat_interval
        self._enabled = True

    async def run(self) -> None:
        """Open core.sock, register, serve pulse.* + heartbeat until dropped."""
        raise NotImplementedError
