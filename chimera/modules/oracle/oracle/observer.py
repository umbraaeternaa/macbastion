"""Mode A — passive pattern learning (§5.3).

Receives observed events (from the consumer connection), splits the topic
'<source>.<event_type>', records them into the baseline, and every
`baseline_every` events fires the on_baseline_updated callback so the client
can emit oracle.baseline.updated.

D11 (self-loop guard): events whose topic starts with 'oracle.' are ignored —
ORACLE must not observe and learn from its own output.

STUB — RED slice. __init__ wires args; record() raises NotImplementedError.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from oracle.baseline import BaselineStore

BaselineUpdatedCallback = Callable[[dict[str, Any]], Awaitable[None]]


class Observer:
    """Mode A learner. STUB (RED slice)."""

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

    async def record(self, topic: str, payload: dict[str, Any]) -> None:
        """Record one observed event. topic = '<source>.<event_type>'.

        Ignores self-originated events (D11). Every `baseline_every` recorded
        events invokes on_baseline_updated with {event_count, ...}.
        """
        raise NotImplementedError("Observer.record — RED slice")
