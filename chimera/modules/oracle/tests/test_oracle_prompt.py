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


# -- Explainability (#1, EP-1c / EP-3) --------------------------------------


def test_response_schema_has_context_factors():
    # Real data (like RESPONSE_SCHEMA was in Mode B RED): present in RED.
    props = RESPONSE_SCHEMA["properties"]
    assert "context_factors" in props
    assert props["context_factors"]["type"] == "array"
    assert props["context_factors"]["items"]["type"] == "string"
    assert "context_factors" not in RESPONSE_SCHEMA["required"]  # optional (EP-1)


def test_build_prompt_includes_derived_factors():
    factors = {"source_seen_before": False, "days_observed": 30, "hour_frequency": 0}
    prompt = build_prompt(EVENT, SUMMARY, factors)
    assert "days_observed" in prompt
    assert "source_seen_before" in prompt


def test_build_prompt_has_directive():
    low = build_prompt(EVENT, SUMMARY).lower()
    assert "time of day" in low or "how many days" in low or "is new" in low
