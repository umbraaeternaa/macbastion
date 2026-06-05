"""Advisory-only invariant (EP-8, D4): classify reads, never acts/mutates.

A regression guard — the property already holds (classify is read-only), so this
passes today; it locks the invariant against future explainability changes.
No core, mock LLM.
"""

from oracle.baseline import BaselineStore
from oracle.detector import Detector
from oracle.query import TimeMachine


class _FakeLlm:
    @property
    def model(self):
        return "fake"

    def available(self):
        return True

    def generate(self, prompt, schema, *, temperature=0.0, num_predict=200):
        return '{"score":0.9,"reasoning":"x","context_factors":[]}'


async def test_classify_does_not_mutate_baseline(tmp_path):
    store = BaselineStore(tmp_path / "b.db", tmp_path / "b.key")
    store.record_event(
        ts="2026-06-04T03:00:00+00:00", source="chaff", event_type="request.sent", payload={}
    )
    before = store.event_count()
    det = Detector(_FakeLlm(), store)
    await det.classify({"source": "chaff", "type": "request.sent"})
    assert store.event_count() == before  # advisory: classify never records/acts


async def test_query_does_not_mutate_baseline(tmp_path):
    store = BaselineStore(tmp_path / "b.db", tmp_path / "b.key")
    store.record_event(
        ts="2026-06-01T10:00:00+00:00", source="chaff", event_type="request.sent", payload={}
    )
    before = store.event_count()
    tm = TimeMachine(store)
    await tm.first_seen("chaff")
    await tm.period_summary("2026-06-01", "2026-06-02")
    assert store.event_count() == before  # advisory: queries are read-only
