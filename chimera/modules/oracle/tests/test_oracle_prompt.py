"""Unit: prompt template + response schema (§5.3 Mode B, MD-B-3c/MD-B-4a).

RESPONSE_SCHEMA is real data (its shape test passes in RED). build_prompt is a
stub -> its tests fail in RED. No core, no Ollama.
"""

from oracle.prompt import RESPONSE_SCHEMA, build_prompt

EVENT = {"source": "chaff", "type": "request.sent", "payload": {"url": "https://x"}}
SUMMARY = {"total": 42, "by_source": {"chaff": 42}, "by_type": {"request.sent": 42}}


def test_response_schema_shape():
    # Real data — intentionally complete in RED (MD-B-4a structured output).
    assert RESPONSE_SCHEMA["type"] == "object"
    assert set(RESPONSE_SCHEMA["required"]) == {"score", "reasoning"}
    assert RESPONSE_SCHEMA["properties"]["score"]["type"] == "number"
    assert RESPONSE_SCHEMA["properties"]["reasoning"]["type"] == "string"


def test_build_prompt_contains_event():
    prompt = build_prompt(EVENT, SUMMARY)
    assert "chaff" in prompt
    assert "request.sent" in prompt


def test_build_prompt_contains_summary_context():
    prompt = build_prompt(EVENT, SUMMARY)
    assert "42" in prompt  # baseline summary count surfaced in the prompt
