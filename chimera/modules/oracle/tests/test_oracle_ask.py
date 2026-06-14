"""Unit: Asker — NL ask routing (#2 Layer 2, NL-1b).

Mock the LLM's intent (canned JSON) so dispatch is deterministic — assert exact
routing/fallback. Against the stub (ask raises) the behavioral tests fail; the
INTENT_SCHEMA shape test passes (real data). No real Ollama.
"""

import pytest
from core.errors import ChimeraError, RpcError
from oracle.ask import INTENT_SCHEMA, Asker
from oracle.baseline import BaselineStore
from oracle.llm import LlmUnavailableError
from oracle.query import TimeMachine


def _store(tmp_path):
    return BaselineStore(tmp_path / "b.db", tmp_path / "b.key")


def _rec(store, ts, source, etype):
    store.record_event(ts=ts, source=source, event_type=etype, payload={})


class FakeLlm:
    """Returns a canned intent JSON string; or simulates an unreachable server."""

    def __init__(self, response, *, down=False):
        self._response = response
        self._down = down

    @property
    def model(self):
        return "fake"

    def available(self):
        return not self._down

    def generate(self, prompt, schema, *, temperature=0.0, num_predict=200):
        if self._down:
            raise LlmUnavailableError("down")
        return self._response


def test_intent_schema_has_query_type_enum():
    # Real data (present in RED).
    enum = INTENT_SCHEMA["properties"]["query_type"]["enum"]
    assert set(enum) == {"first_seen", "period", "unknown"}
    assert INTENT_SCHEMA["required"] == ["query_type"]


def test_parse_intent_salvages_fenced_intent():
    # A ```json-fenced but otherwise valid intent should route, not degrade to 'unknown'
    # (mirrors detector salvage — robustness for a 7B model that decorates its output).
    intent = Asker._parse_intent('```json\n{"query_type":"first_seen","source":"chaff"}\n```')
    assert intent["query_type"] == "first_seen"
    assert intent["source"] == "chaff"


def test_parse_intent_unrecoverable_degrades_to_unknown():
    # Genuinely unparseable -> the safe graceful degrade is preserved (no fabricated intent).
    assert Asker._parse_intent("not json at all")["query_type"] == "unknown"


async def test_ask_routes_first_seen(tmp_path):
    store = _store(tmp_path)
    _rec(store, "2026-06-01T10:00:00+00:00", "chaff", "request.sent")
    llm = FakeLlm('{"query_type":"first_seen","source":"chaff"}')
    result = await Asker(llm, TimeMachine(store)).ask("when did chaff first appear?")
    assert result["query_used"] == "first_seen"
    assert result["raw_result"]["first_seen"] == "2026-06-01T10:00:00+00:00"
    assert "chaff" in result["answer"]


async def test_ask_routes_period(tmp_path):
    store = _store(tmp_path)
    _rec(store, "2026-06-02T10:00:00+00:00", "chaff", "request.sent")
    llm = FakeLlm('{"query_type":"period","start":"2026-06-02","end":"2026-06-03"}')
    result = await Asker(llm, TimeMachine(store)).ask("how many events on the 2nd?")
    assert result["query_used"] == "period"
    assert result["raw_result"]["total"] == 1


async def test_ask_unknown_intent(tmp_path):
    llm = FakeLlm('{"query_type":"unknown"}')
    result = await Asker(llm, TimeMachine(_store(tmp_path))).ask("meaning of life?")
    assert result["query_used"] == "unknown"
    assert result["raw_result"] is None


async def test_ask_invalid_params_falls_back_to_unknown(tmp_path):
    # first_seen without source -> cannot run -> unknown (no garbage query)
    llm = FakeLlm('{"query_type":"first_seen"}')
    result = await Asker(llm, TimeMachine(_store(tmp_path))).ask("when first?")
    assert result["query_used"] == "unknown"


async def test_ask_malformed_intent_falls_back_to_unknown(tmp_path):
    result = await Asker(FakeLlm("not json"), TimeMachine(_store(tmp_path))).ask("???")
    assert result["query_used"] == "unknown"


async def test_ask_gate_when_ollama_down(tmp_path):
    asker = Asker(FakeLlm("", down=True), TimeMachine(_store(tmp_path)))
    with pytest.raises(RpcError) as exc:
        await asker.ask("when did chaff appear?")
    assert exc.value.code == ChimeraError.PRECONDITION_FAILED  # -31004
