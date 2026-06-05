"""Behavioral Time-Machine — structured baseline queries (#2, TM-1c Layer 1).

Read-only orchestration over BaselineStore: validates/shapes; the SQL lives in
baseline.py (which owns the connection). Deterministic — NO LLM this slice
(TM-5a). advisory-only (TM-10): returns data, never acts. The blocking store
calls are off-loaded via asyncio.to_thread (consistent with the detector).

STUB — RED slice. __init__ wires the store; queries raise NotImplementedError.
"""

from typing import Any

from oracle.baseline import BaselineStore


class TimeMachine:
    """Structured time-range queries over the baseline (#2). STUB (RED slice)."""

    def __init__(self, store: BaselineStore) -> None:
        self._store = store

    async def first_seen(
        self, source: str, event_type: str | None = None
    ) -> dict[str, Any]:
        """Earliest occurrence of a source (optionally a type)."""
        raise NotImplementedError("TimeMachine.first_seen — RED slice")

    async def period_summary(self, start: str, end: str) -> dict[str, Any]:
        """Event counts in the half-open window [start, end)."""
        raise NotImplementedError("TimeMachine.period_summary — RED slice")
