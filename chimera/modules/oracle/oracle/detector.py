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
import re
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

# Salvage patterns for a fenced/truncated LLM response (a 7B model occasionally cuts the JSON
# off mid-string or wraps it in a ```json fence). The reasoning pattern tolerates an
# unterminated string (truncated mid-value).
_SCORE_RE = re.compile(r'"score"\s*:\s*(-?[0-9]+(?:\.[0-9]+)?)')
_REASONING_RE = re.compile(r'"reasoning"\s*:\s*"((?:[^"\\]|\\.)*)')


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
        days = await asyncio.to_thread(self._store.days_observed)
        factors = self._derive_factors(event, summary, days)
        prompt = build_prompt(event, {**summary, "recent_events": recent}, factors)
        try:
            raw = await asyncio.to_thread(
                self._llm.generate, prompt, RESPONSE_SCHEMA
            )
        except LlmUnavailableError as e:
            raise RpcError(code=ChimeraError.PRECONDITION_FAILED) from e
        result = self._parse(raw)
        result["similar_events"] = self._similar(event, recent)
        return result

    @staticmethod
    def _derive_factors(
        event: dict[str, Any], summary: dict[str, Any], days_observed: int
    ) -> dict[str, Any]:
        """Deterministic explainability signals fed into the prompt (EP-3)."""
        source = event.get("source")
        event_type = event.get("type")
        ts = event.get("ts")
        hour = ts[11:13] if isinstance(ts, str) and len(ts) >= 13 else None
        by_hour = summary.get("by_hour", {})
        return {
            "source_seen_before": source in summary.get("by_source", {}),
            "type_seen_before": event_type in summary.get("by_type", {}),
            "event_hour": hour,
            "hour_frequency": by_hour.get(hour, 0) if hour is not None else None,
            "days_observed": days_observed,
        }

    @staticmethod
    def _similar(
        event: dict[str, Any], recent: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Naive top-3 baseline matches: same source+type (EP-4a; embeddings = v2)."""
        source = event.get("source")
        event_type = event.get("type")
        matches = [
            {"ts": e["ts"], "source": e["source"], "type": e["type"]}
            for e in recent
            if e["source"] == source and e["type"] == event_type
        ]
        return matches[:3]

    @staticmethod
    def _parse(raw: str) -> dict[str, Any]:
        """Parse structured JSON into {score (clamped), reasoning, context_factors}.

        context_factors is lenient (EP-1): a missing/invalid array defaults to []
        — a 1B model may omit it. score/reasoning stay strict (MD-B-4a).

        Robustness: a 7B model occasionally wraps the object in a ```json fence or cuts it off
        mid-string. We try strict json.loads first, then salvage (trim to the outermost object,
        else regex-extract the score). Only a response with NO recoverable score is malformed and
        still raises (MANIFESTO §4 — we never invent a score).
        """
        try:
            data = json.loads(raw)
            score = float(data["score"])
            reasoning = str(data["reasoning"])
            factors = data.get("context_factors", [])
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            salvaged = Detector._salvage(raw)
            if salvaged is None:
                raise RpcError(
                    code=JSONRPC_INTERNAL_ERROR, message="LLM returned malformed output"
                ) from e
            score, reasoning, factors = salvaged
        if not isinstance(factors, list) or not all(isinstance(x, str) for x in factors):
            factors = []
        return {
            "score": max(0.0, min(1.0, score)),
            "reasoning": reasoning,
            "context_factors": factors,
        }

    @staticmethod
    def _salvage(raw: str) -> tuple[float, str, list[str]] | None:
        """Best-effort recovery from a fenced/truncated response: returns (score, reasoning,
        factors) when a score is extractable, else None — never invents one."""
        # 1) Trim a ```json fence / surrounding prose to the outermost {...} and retry.
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end > start:
            try:
                obj = json.loads(raw[start : end + 1])
                return float(obj["score"]), str(obj.get("reasoning", "")), obj.get(
                    "context_factors", []
                )
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                pass
        # 2) Truncated mid-object (no usable closing brace): regex-pull the score (+ reasoning).
        m = _SCORE_RE.search(raw)
        if m is None:
            return None
        try:
            score = float(m.group(1))
        except ValueError:
            return None
        rm = _REASONING_RE.search(raw)
        reasoning = rm.group(1) if rm else "(recovered from truncated output)"
        return score, reasoning, []

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
