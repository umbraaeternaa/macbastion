"""Prompt template + response schema for Mode B (§5.3, MD-B-3c / MD-B-4a).

RESPONSE_SCHEMA is REAL data (passed to Ollama's structured-output `format=`),
not a stub. build_prompt is a STUB — RED slice.
"""

import json
from typing import Any

# MD-B-4a: structured output — the model must return exactly this shape.
RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "score": {"type": "number", "minimum": 0, "maximum": 1},
        "reasoning": {"type": "string"},
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


def build_prompt(event: dict[str, Any], summary: dict[str, Any]) -> str:
    """Build the classification prompt: generic template + structured context.

    MD-B-3c — the spec question, with the event and the baseline summary as
    JSON context blocks (compact, sorted keys for determinism).
    """
    return _TEMPLATE.format(
        summary=json.dumps(summary, sort_keys=True),
        event=json.dumps(event, sort_keys=True),
    )
