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

When you explain, cite concrete personal context: the time of day versus the \
user's usual hours, how many days the baseline spans, and whether this source \
or type is new. Return context_factors as a short list of such factors.

Baseline summary (JSON):
{summary}
{factors_block}
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
    derived explainability signals (EP-3) — surfaced as a "Derived facts" block.
    """
    factors_block = (
        f"\nDerived facts (JSON):\n{json.dumps(factors, sort_keys=True)}\n"
        if factors is not None
        else ""
    )
    return _TEMPLATE.format(
        summary=json.dumps(summary, sort_keys=True),
        event=json.dumps(event, sort_keys=True),
        factors_block=factors_block,
    )
