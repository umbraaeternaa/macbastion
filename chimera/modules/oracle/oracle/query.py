"""Behavioral Time-Machine — structured baseline queries (#2, TM-1c Layer 1).

Read-only orchestration over BaselineStore: validates/shapes; the SQL lives in
baseline.py (which owns the connection). Deterministic — NO LLM this slice
(TM-5a). advisory-only (TM-10): returns data, never acts. The blocking store
calls are off-loaded via asyncio.to_thread (consistent with the detector).

GREEN: __init__ wires the store; first_seen / period_summary return real shaped data.
"""

import asyncio
from typing import Any

from oracle.baseline import BaselineStore


class TimeMachine:
    """Structured time-range queries over the baseline (#2)."""

    def __init__(self, store: BaselineStore) -> None:
        self._store = store

    async def first_seen(
        self, source: str, event_type: str | None = None
    ) -> dict[str, Any]:
        """Earliest occurrence of a source (optionally a type)."""
        ts = await asyncio.to_thread(self._store.first_seen, source, event_type)
        return {"source": source, "event_type": event_type, "first_seen": ts}

    async def period_summary(self, start: str, end: str) -> dict[str, Any]:
        """Event counts in the half-open window [start, end)."""
        summary = await asyncio.to_thread(self._store.period_summary, start, end)
        return {"start": start, "end": end, **summary}
