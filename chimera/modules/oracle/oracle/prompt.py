"""Prompt template + response schema for Mode B (§5.3, MD-B-3c / MD-B-4a).

RESPONSE_SCHEMA is REAL data (passed to Ollama's structured-output `format=`).
build_prompt is GREEN — it fills the template from the event + baseline summary.
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
You are a security anomaly detector for a single user's machine. Score how \
anomalous and dangerous the event is, from 0.0 (perfectly normal) to 1.0 \
(clearly malicious or destructive). Put the NUMBER in the `score` field — make it \
match how dangerous your reasoning says the event is.

Scoring guide (anchors):
- 0.0-0.2  routine, expected (normal app use, usual login hours).
- 0.3-0.5  mildly unusual (a new app, off-hours but plausible).
- 0.6-0.8  suspicious (unrecognized process, unusual data access, odd network).
- 0.9-1.0  clearly malicious/destructive — ransomware or mass file encryption, \
data exfiltration, deleting backups/shadow copies, credential theft.

Examples:
- Event: user opens their browser at 2pm.  ->  score 0.05
- Event: 8000 files encrypted to .locked, ransom note written, shadow copies \
deleted.  ->  score 0.97
- Event: 2GB uploaded to an unknown host over Tor at 3am.  ->  score 0.9

Use the user's baseline below for context. Cite concrete factors: time of day \
versus usual hours, how many days the baseline spans, whether this source or type \
is new. Return context_factors as a short list of such factors.

Baseline summary (JSON):
{summary}
{factors_block}
Event (JSON):
{event}

Now set `score` (0.0-1.0) for THIS event and explain why. Make the number match \
the danger your reasoning describes — high only for genuinely suspicious or \
destructive events, low for routine, in-baseline activity. Do not output 0 for an \
event your reasoning calls dangerous, and do not over-flag normal activity."""


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
