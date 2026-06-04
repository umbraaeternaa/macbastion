"""Prompt template + response schema for Mode B (§5.3, MD-B-3c / MD-B-4a).

RESPONSE_SCHEMA is REAL data (passed to Ollama's structured-output `format=`),
not a stub. build_prompt is a STUB — RED slice.
"""

import json
from typing import Any

# MD-B-4a: structured output. context_factors (EP-1c) is in properties but NOT
# required — a 1B model may omit it; the parser defaults it to [] (lenient,
# backward-compatible with Mode B fakes). Asymmetric with score/reasoning by design.
RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "score": {"type": "number", "minimum": 0, "maximum": 1},
        "reasoning": {"type": "string"},
        "context_factors": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["score", "reasoning"],
}


_TEMPLATE = """\
You are a security anomaly detector observing a single user's machine.
Given the user's normal pattern (baseline summary) below, decide whether the \
following event is unusual. Reply with a score from 0 (perfectly normal) to 1 \
(highly anomalous) and a short reasoning.

Baseline summary (JSON):
{summary}

Event (JSON):
{event}

Score the event 0-1 and explain why."""


def build_prompt(
    event: dict[str, Any],
    summary: dict[str, Any],
    factors: dict[str, Any] | None = None,
) -> str:
    """Build the classification prompt: generic template + structured context.

    MD-B-3c — the spec question, with the event and the baseline summary as
    JSON context blocks (compact, sorted keys for determinism). `factors` carries
    derived explainability signals (EP-3) — wired in GREEN; ignored in this slice.
    """
    return _TEMPLATE.format(
        summary=json.dumps(summary, sort_keys=True),
        event=json.dumps(event, sort_keys=True),
    )
