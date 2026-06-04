"""Prompt template + response schema for Mode B (§5.3, MD-B-3c / MD-B-4a).

RESPONSE_SCHEMA is REAL data (passed to Ollama's structured-output `format=`),
not a stub. build_prompt is a STUB — RED slice.
"""

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


def build_prompt(event: dict[str, Any], summary: dict[str, Any]) -> str:
    """Build the classification prompt: generic template + structured context.

    MD-B-3c — the spec question, with the event and the baseline summary as
    JSON context blocks.
    """
    raise NotImplementedError("build_prompt — RED slice")
