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

import asyncio
import json
from typing import Any

from core.errors import (
    JSONRPC_INTERNAL_ERROR,
    JSONRPC_INVALID_PARAMS,
    ChimeraError,
    RpcError,
)

from oracle.baseline import BaselineStore
from oracle.llm import LlmClient, LlmUnavailableError
from oracle.prompt import RESPONSE_SCHEMA, build_prompt

DEFAULT_THRESHOLD = 0.7
RECENT_LIMIT = 50


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

    @property
    def llm(self) -> LlmClient:
        """The underlying LLM client (used by the client's startup probe)."""
        return self._llm

    async def classify(self, event: dict[str, Any]) -> dict[str, Any]:
        """Classify one event -> {score, reasoning} (advisory; never acts).

        Builds baseline context, runs the LLM (off-loop via to_thread), parses
        the structured JSON. Ollama down -> -31004 (D6). Malformed JSON ->
        INTERNAL_ERROR (MD-B-4a: no fake 0.5).
        """
        summary = await asyncio.to_thread(self._store.summary)
        recent = await asyncio.to_thread(self._store.recent_events, RECENT_LIMIT)
        prompt = build_prompt(event, {**summary, "recent_events": recent})
        try:
            raw = await asyncio.to_thread(
                self._llm.generate, prompt, RESPONSE_SCHEMA
            )
        except LlmUnavailableError as e:
            raise RpcError(code=ChimeraError.PRECONDITION_FAILED) from e
        return self._parse(raw)

    @staticmethod
    def _parse(raw: str) -> dict[str, Any]:
        """Parse the LLM's structured JSON into {score (clamped), reasoning}."""
        try:
            data = json.loads(raw)
            score = float(data["score"])
            reasoning = str(data["reasoning"])
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            raise RpcError(
                code=JSONRPC_INTERNAL_ERROR, message="LLM returned malformed output"
            ) from e
        return {"score": max(0.0, min(1.0, score)), "reasoning": reasoning}

    def get_threshold(self) -> float:
        """Current anomaly threshold (baseline_meta, falls back to the seed)."""
        value = self._store.get_meta("threshold")
        return float(value) if value is not None else self._threshold

    def set_threshold(self, value: float) -> dict[str, Any]:
        """Persist a new threshold (0..1); return the updated config."""
        if not 0.0 <= value <= 1.0:
            raise RpcError(
                code=JSONRPC_INVALID_PARAMS, message="threshold must be in 0..1"
            )
        self._store.set_meta("threshold", str(value))
        return {"threshold": value}
