"""Mode B — anomaly detector (§5.3, MD-B-1).

advisory-only (D4): classify returns {score, reasoning}; it never acts.
Manual-only (MD-B-2a): invoked via oracle.classify, NOT per-event — Mode A
learning is independent and must not depend on this.

Flow (GREEN): build context (store.recent_events + store.summary) -> prompt ->
llm.generate (structured output, wrapped in asyncio.to_thread) -> json.loads ->
clamp score. Ollama down -> LlmUnavailableError -> RpcError(-31004) (D6 per-call).
Threshold persisted in baseline_meta('threshold'), default 0.7 (MD-B-8a).

STUB — RED slice. __init__ wires deps; classify/get_threshold/set_threshold
raise NotImplementedError.
"""

from typing import Any

from oracle.baseline import BaselineStore
from oracle.llm import LlmClient

DEFAULT_THRESHOLD = 0.7


class Detector:
    """Mode B classifier (§5.3). STUB (RED slice)."""

    def __init__(
        self,
        llm: LlmClient,
        store: BaselineStore,
        *,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> None:
        self._llm = llm
        self._store = store
        self._threshold = threshold

    async def classify(self, event: dict[str, Any]) -> dict[str, Any]:
        """Classify one event -> {score, reasoning}. -31004 if Ollama down."""
        raise NotImplementedError("Detector.classify — RED slice")

    def get_threshold(self) -> float:
        """Current anomaly threshold (baseline_meta, default 0.7)."""
        raise NotImplementedError("Detector.get_threshold — RED slice")

    def set_threshold(self, value: float) -> dict[str, Any]:
        """Persist a new threshold; return the updated config."""
        raise NotImplementedError("Detector.set_threshold — RED slice")
