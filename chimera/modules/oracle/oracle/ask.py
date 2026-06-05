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

from typing import Any

from oracle.llm import LlmClient
from oracle.query import TimeMachine

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
        """Map a question to a query, run it, return {answer, query_used, raw_result}."""
        raise NotImplementedError("Asker.ask — RED slice")
