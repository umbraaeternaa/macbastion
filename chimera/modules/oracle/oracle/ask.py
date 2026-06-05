"""Time-Machine Layer 2 — NL ask (#2, NL-1b structured intent).

Asker composes the Mode B LlmClient (intent extraction via format=schema) with
the LLM-free Layer 1 TimeMachine (deterministic queries). ONE LLM call (intent);
the answer is code-templated this slice (NL-2a) — LLM narration is a later
sub-slice. advisory-only (read + LLM, never acts).

Routing safety: query_type is an enum, so the model cannot invent a query that
does not exist — but it CAN mis-route to the wrong allowed query or mis-extract
params (empirically: a 1B model answered "whatsapp" to a "chaff" question).
raw_result is returned verbatim as the transparent safeguard. Unmappable /
unsure / malformed → "unknown" (an honest "don't know" beats guessing, NL-4a).
Ollama down → -31004 (NL-7).

STUB — RED slice. __init__ wires deps; ask() raises NotImplementedError.
INTENT_SCHEMA is real data (present in RED).
"""

import asyncio
import json
from typing import Any

from core.errors import ChimeraError, RpcError

from oracle.llm import LlmClient, LlmUnavailableError
from oracle.query import TimeMachine

_INTENT_PROMPT = """\
You map a user's question about their own activity history to ONE query.
query_type must be one of:
- "first_seen": when a source (optionally a type) was first seen — needs `source`.
- "period": event counts in a date window — needs `start` and `end` (YYYY-MM-DD).
- "unknown": the question maps to neither.
Fill only the relevant params; use "unknown" if unsure.

Question: {question}"""

# NL-3a: flat structured-intent schema. The enum constrains query_type to the
# known set (+ "unknown" honest fallback) — the model cannot return a
# nonexistent query.
INTENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query_type": {
            "type": "string",
            "enum": ["first_seen", "period", "unknown"],
        },
        "source": {"type": "string"},
        "event_type": {"type": "string"},
        "start": {"type": "string"},
        "end": {"type": "string"},
    },
    "required": ["query_type"],
}


class Asker:
    """NL question -> structured intent -> Layer 1 query -> answer. STUB (RED)."""

    def __init__(self, llm: LlmClient, timemachine: TimeMachine) -> None:
        self._llm = llm
        self._timemachine = timemachine

    async def ask(self, question: str) -> dict[str, Any]:
        """Map a question to a query, run it, return {answer, query_used, raw_result}.

        Ollama down -> -31004 (NL-7). Malformed/unsure/invalid-params -> "unknown"
        (NL-4a — honest "don't know" beats guessing). raw_result is returned
        verbatim as the transparent safeguard against semantic mis-routing.
        """
        prompt = _INTENT_PROMPT.format(question=question)
        try:
            raw = await asyncio.to_thread(self._llm.generate, prompt, INTENT_SCHEMA)
        except LlmUnavailableError as e:
            raise RpcError(code=ChimeraError.PRECONDITION_FAILED) from e

        intent = self._parse_intent(raw)
        query_type = intent.get("query_type")

        if query_type == "first_seen" and isinstance(intent.get("source"), str):
            event_type = intent.get("event_type")
            event_type = event_type if isinstance(event_type, str) else None
            raw_result = await self._timemachine.first_seen(intent["source"], event_type)
            return self._shape("first_seen", raw_result)

        if (
            query_type == "period"
            and isinstance(intent.get("start"), str)
            and isinstance(intent.get("end"), str)
        ):
            raw_result = await self._timemachine.period_summary(
                intent["start"], intent["end"]
            )
            return self._shape("period", raw_result)

        # unknown query_type, or required params missing/invalid (NL-4a/NL-5)
        return self._shape("unknown", None)

    @staticmethod
    def _parse_intent(raw: str) -> dict[str, Any]:
        """Parse the LLM intent; any failure degrades to {'query_type': 'unknown'}."""
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {"query_type": "unknown"}
        if not isinstance(data, dict) or data.get("query_type") not in (
            "first_seen",
            "period",
            "unknown",
        ):
            return {"query_type": "unknown"}
        return data

    @staticmethod
    def _shape(query_used: str, raw_result: dict[str, Any] | None) -> dict[str, Any]:
        """Build the code-templated answer (NL-2a — deterministic, no LLM narration)."""
        answer = "I couldn't map that question to a supported query (first_seen or period)."
        if query_used == "first_seen" and raw_result is not None:
            source = raw_result["source"]
            ts = raw_result["first_seen"]
            answer = (
                f"'{source}' was first seen at {ts}."
                if ts is not None
                else f"No '{source}' events in the baseline yet."
            )
        elif query_used == "period" and raw_result is not None:
            answer = (
                f"Between {raw_result['start']} and {raw_result['end']} "
                f"there were {raw_result['total']} events."
            )
        return {"answer": answer, "query_used": query_used, "raw_result": raw_result}
