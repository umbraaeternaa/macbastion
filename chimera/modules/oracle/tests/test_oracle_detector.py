"""Unit: Detector — Mode B classify (§5.3, MD-B-1/2/4/6/8).

FakeLlm is injected (DI) so no real Ollama is needed; threshold tests use a real
BaselineStore (meta-backed, MD-B-8a). Against the stub (classify/get/set raise
NotImplementedError) every assertion fails — RED.
"""

import pytest
from core.errors import JSONRPC_INTERNAL_ERROR, ChimeraError, RpcError
from oracle.baseline import BaselineStore
from oracle.detector import Detector
from oracle.llm import LlmUnavailableError

EVENT = {"source": "chaff", "type": "request.sent", "payload": {"url": "https://x"}}


class FakeLlm:
    """Duck-typed LlmClient: canned response, controllable availability."""

    def __init__(self, response='{"score": 0.9, "reasoning": "unusual gap"}', *, down=False):
        self._response = response
        self._down = down
        self.calls = []

    @property
    def model(self):
        return "fake-model"

    def available(self):
        return not self._down

    def generate(self, prompt, schema, *, temperature=0.0, num_predict=200):
        if self._down:
            raise LlmUnavailableError("server down")
        self.calls.append({"prompt": prompt, "schema": schema})
        return self._response


def _store(tmp_path):
    return BaselineStore(tmp_path / "baseline.db", tmp_path / "baseline.key")


async def test_classify_returns_score_and_reasoning(tmp_path):
    det = Detector(FakeLlm(), _store(tmp_path))
    result = await det.classify(EVENT)
    assert result["score"] == 0.9
    assert result["reasoning"] == "unusual gap"


async def test_classify_calls_llm_with_response_schema(tmp_path):
    from oracle.prompt import RESPONSE_SCHEMA

    llm = FakeLlm()
    det = Detector(llm, _store(tmp_path))
    await det.classify(EVENT)
    assert llm.calls and llm.calls[0]["schema"] == RESPONSE_SCHEMA


async def test_classify_clamps_score(tmp_path):
    det = Detector(FakeLlm('{"score": 1.5, "reasoning": "x"}'), _store(tmp_path))
    result = await det.classify(EVENT)
    assert result["score"] == 1.0


async def test_classify_gate_when_unavailable(tmp_path):
    det = Detector(FakeLlm(down=True), _store(tmp_path))
    with pytest.raises(RpcError) as exc:
        await det.classify(EVENT)
    assert exc.value.code == ChimeraError.PRECONDITION_FAILED  # -31004


async def test_classify_malformed_json_raises_internal(tmp_path):
    det = Detector(FakeLlm("not json at all"), _store(tmp_path))
    with pytest.raises(RpcError) as exc:
        await det.classify(EVENT)
    assert exc.value.code == JSONRPC_INTERNAL_ERROR  # MD-B-4a: no fake 0.5


def test_threshold_default_and_set(tmp_path):
    det = Detector(FakeLlm(), _store(tmp_path))
    assert det.get_threshold() == 0.7
    det.set_threshold(0.5)
    assert det.get_threshold() == 0.5


# -- Explainability (#1) ----------------------------------------------------


async def test_classify_returns_context_factors(tmp_path):
    llm = FakeLlm('{"score":0.5,"reasoning":"x","context_factors":["off-hours","new source"]}')
    det = Detector(llm, _store(tmp_path))
    result = await det.classify(EVENT)
    assert result["context_factors"] == ["off-hours", "new source"]


async def test_classify_context_factors_defaults_empty(tmp_path):
    # LLM omits context_factors -> lenient parse returns [] (EP-1, asymmetry).
    det = Detector(FakeLlm('{"score":0.5,"reasoning":"x"}'), _store(tmp_path))
    result = await det.classify(EVENT)
    assert result["context_factors"] == []


async def test_classify_returns_similar_events(tmp_path):
    store = _store(tmp_path)
    store.record_event(
        ts="2026-06-04T03:00:00+00:00", source="chaff", event_type="request.sent", payload={"n": 1}
    )
    store.record_event(
        ts="2026-06-04T04:00:00+00:00", source="chaff", event_type="request.sent", payload={"n": 2}
    )
    store.record_event(
        ts="2026-06-04T05:00:00+00:00", source="mirror", event_type="move", payload={}
    )
    det = Detector(FakeLlm(), store)
    result = await det.classify(EVENT)  # EVENT = chaff / request.sent
    sims = result["similar_events"]
    assert len(sims) == 2  # both chaff/request.sent; mirror excluded
    assert all(s["source"] == "chaff" and s["type"] == "request.sent" for s in sims)


async def test_classify_prompt_includes_derived_factors(tmp_path):
    llm = FakeLlm()
    det = Detector(llm, _store(tmp_path))
    await det.classify(EVENT)
    prompt = llm.calls[0]["prompt"]
    assert "days_observed" in prompt
    assert "source_seen_before" in prompt
