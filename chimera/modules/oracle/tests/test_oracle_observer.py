"""Unit: Observer — Mode A learning (§5.3).

Verifies record() writes through to the store, the D11 self-loop guard
(oracle.* ignored), and the baseline_every callback (fires at the threshold,
not before). Uses a duck-typed FakeStore to stay isolated from BaselineStore.
No core, no Ollama.
"""

from oracle.observer import Observer


class FakeStore:
    """Minimal duck-typed store recording record_event calls."""

    def __init__(self):
        self.events = []

    def record_event(self, *, ts, source, event_type, payload, context=None):
        self.events.append((source, event_type, payload))
        return len(self.events)

    def event_count(self):
        return len(self.events)


async def test_record_writes_to_store():
    store = FakeStore()
    obs = Observer(store, baseline_every=100)
    await obs.record("chaff.request.sent", {"url": "https://example"})
    assert store.event_count() == 1
    assert store.events[0][0] == "chaff"
    assert store.events[0][1] == "request.sent"


async def test_self_loop_guard_ignores_oracle_topics():
    store = FakeStore()
    obs = Observer(store, baseline_every=100)
    await obs.record("oracle.baseline.updated", {"event_count": 3})
    assert store.event_count() == 0  # D11: ORACLE ignores its own events


async def test_baseline_every_fires_callback():
    fired = []

    async def on_updated(payload):
        fired.append(payload)

    store = FakeStore()
    obs = Observer(store, baseline_every=3, on_baseline_updated=on_updated)
    for _ in range(3):
        await obs.record("chaff.request.sent", {})
    assert len(fired) == 1
    assert fired[0]["event_count"] == 3


async def test_callback_not_fired_before_threshold():
    fired = []

    async def on_updated(payload):
        fired.append(payload)

    store = FakeStore()
    obs = Observer(store, baseline_every=5, on_baseline_updated=on_updated)
    for _ in range(4):
        await obs.record("chaff.request.sent", {})
    assert fired == []
