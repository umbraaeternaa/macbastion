"""Mode A — passive pattern learning (§5.3).

Receives observed events (from the consumer connection), splits the topic
'<source>.<event_type>', records them into the baseline, and every
`baseline_every` events fires the on_baseline_updated callback so the client
can emit oracle.baseline.updated.

D11 (self-loop guard): events whose topic starts with 'oracle.' are ignored —
ORACLE must not observe and learn from its own output.

The store is blocking SQLite, so the synchronous DB work is pushed to a worker
thread via asyncio.to_thread (D0); the event loop is never blocked. The
on_baseline_updated callback runs back on the loop (it writes to a socket).
"""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from oracle.baseline import BaselineStore

BaselineUpdatedCallback = Callable[[dict[str, Any]], Awaitable[None]]


class Observer:
    """Mode A learner (§5.3)."""

    SELF_PREFIX = "oracle."

    def __init__(
        self,
        store: BaselineStore,
        *,
        baseline_every: int = 100,
        on_baseline_updated: BaselineUpdatedCallback | None = None,
    ) -> None:
        self._store = store
        self._baseline_every = baseline_every
        self._on_baseline_updated = on_baseline_updated

    async def record(
        self,
        topic: str,
        payload: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> None:
        """Record one observed event. topic = '<source>.<event_type>'.

        Ignores self-originated events (D11). Every `baseline_every` recorded
        events invokes on_baseline_updated with {event_count, ...}.
        """
        if topic.startswith(self.SELF_PREFIX):
            return  # D11: never learn from our own output
        count = await asyncio.to_thread(self._record_sync, topic, payload, context)
        if count % self._baseline_every == 0 and self._on_baseline_updated is not None:
            await self._on_baseline_updated(
                {"event_count": count, "baseline_summary": {"events": count}}
            )

    def _record_sync(
        self,
        topic: str,
        payload: dict[str, Any],
        context: dict[str, Any] | None,
    ) -> int:
        """Blocking store write (runs in a worker thread); returns new count."""
        source, _, event_type = topic.partition(".")
        self._store.record_event(
            ts=self._utc_now(),
            source=source,
            event_type=event_type,
            payload=payload,
            context=context,
        )
        return self._store.event_count()

    @staticmethod
    def _utc_now() -> str:
        """Current UTC timestamp, ISO-8601. Isolated for testability."""
        return datetime.now(UTC).isoformat()
