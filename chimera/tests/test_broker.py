"""Tests for broker module (§6.6 event subscription + §6.8 backpressure)."""

import asyncio
from asyncio import QueueEmpty

import pytest
from core.broker import Event, EventBroker, Subscription, SubscriptionClosedError
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# Subscribe — registration mechanics
# ---------------------------------------------------------------------------


class TestSubscribe:
    """subscribe() returns a Subscription handle reflecting the requested topics."""

    def test_subscribe_returns_subscription_instance(self) -> None:
        broker = EventBroker()
        sub = broker.subscribe(["test"])
        assert isinstance(sub, Subscription)

    def test_subscribe_with_single_topic(self) -> None:
        broker = EventBroker()
        sub = broker.subscribe(["vault.locked"])
        assert sub.topics == ("vault.locked",)

    def test_subscribe_with_multiple_topics(self) -> None:
        broker = EventBroker()
        sub = broker.subscribe(["vault.locked", "oracle.alert"])
        assert sub.topics == ("vault.locked", "oracle.alert")

    def test_subscribe_with_wildcards(self) -> None:
        broker = EventBroker()
        sub = broker.subscribe(["oracle.*", "*.error"])
        assert sub.topics == ("oracle.*", "*.error")

    def test_subscribe_with_empty_topics_list_raises(self) -> None:
        broker = EventBroker()
        with pytest.raises(ValueError, match="topic"):
            broker.subscribe([])


# ---------------------------------------------------------------------------
# Publish — fan-out to matching subscriptions
# ---------------------------------------------------------------------------


class TestPublish:
    """publish() delivers events to subscribers whose topics match."""

    def test_publish_with_no_subscribers_is_noop(self) -> None:
        broker = EventBroker()
        broker.publish(Event(topic="any", payload={}))  # no error, no observer

    def test_publish_delivers_to_exact_match(self) -> None:
        broker = EventBroker()
        sub = broker.subscribe(["vault.locked"])
        broker.publish(Event(topic="vault.locked", payload={"key": "value"}))
        event = sub.get_nowait()
        assert event.topic == "vault.locked"
        assert event.payload == {"key": "value"}

    def test_publish_delivers_to_wildcard_match(self) -> None:
        broker = EventBroker()
        sub = broker.subscribe(["oracle.*"])
        broker.publish(Event(topic="oracle.alert", payload={}))
        assert sub.get_nowait().topic == "oracle.alert"

    def test_publish_payload_is_pass_through(self) -> None:
        broker = EventBroker()
        payload = {"complex": {"nested": [1, 2, 3]}}
        sub = broker.subscribe(["test"])
        broker.publish(Event(topic="test", payload=payload))
        assert sub.get_nowait().payload == payload


# ---------------------------------------------------------------------------
# Topic matching — three wildcard forms (prefix.*, *.suffix, *) + exact
# ---------------------------------------------------------------------------


class TestTopicMatching:
    """Only three wildcard forms are recognized; everything else is exact-match."""

    def test_exact_match_only(self) -> None:
        broker = EventBroker()
        sub = broker.subscribe(["vault.locked"])
        broker.publish(Event(topic="vault.unlocked", payload={}))
        with pytest.raises(QueueEmpty):
            sub.get_nowait()

    def test_prefix_wildcard_matches(self) -> None:
        broker = EventBroker()
        sub = broker.subscribe(["oracle.*"])
        broker.publish(Event(topic="oracle.alert", payload={}))
        broker.publish(Event(topic="oracle.warning", payload={}))
        assert sub.get_nowait().topic == "oracle.alert"
        assert sub.get_nowait().topic == "oracle.warning"

    def test_prefix_wildcard_does_not_match_other_prefix(self) -> None:
        broker = EventBroker()
        sub = broker.subscribe(["oracle.*"])
        broker.publish(Event(topic="vault.locked", payload={}))
        with pytest.raises(QueueEmpty):
            sub.get_nowait()

    def test_suffix_wildcard_matches(self) -> None:
        broker = EventBroker()
        sub = broker.subscribe(["*.error"])
        broker.publish(Event(topic="oracle.error", payload={}))
        broker.publish(Event(topic="vault.error", payload={}))
        topics = {sub.get_nowait().topic, sub.get_nowait().topic}
        assert topics == {"oracle.error", "vault.error"}

    def test_suffix_wildcard_does_not_match_other_suffix(self) -> None:
        broker = EventBroker()
        sub = broker.subscribe(["*.error"])
        broker.publish(Event(topic="oracle.alert", payload={}))
        with pytest.raises(QueueEmpty):
            sub.get_nowait()

    def test_global_wildcard_matches_everything(self) -> None:
        broker = EventBroker()
        sub = broker.subscribe(["*"])
        broker.publish(Event(topic="anything.at.all", payload={}))
        assert sub.get_nowait().topic == "anything.at.all"

    def test_multiple_patterns_all_match(self) -> None:
        broker = EventBroker()
        sub = broker.subscribe(["oracle.*", "*.error"])
        broker.publish(Event(topic="oracle.warning", payload={}))  # matches oracle.*
        broker.publish(Event(topic="vault.error", payload={}))  # matches *.error
        topics = {sub.get_nowait().topic, sub.get_nowait().topic}
        assert topics == {"oracle.warning", "vault.error"}

    def test_internal_wildcards_treated_as_exact(self) -> None:
        # "a.*.b" is NOT a recognized wildcard form (only prefix.*, *.suffix, *).
        # The broker treats it as a literal exact-match string.
        broker = EventBroker()
        sub = broker.subscribe(["a.*.b"])
        broker.publish(Event(topic="a.x.b", payload={}))  # no match (not literal)
        with pytest.raises(QueueEmpty):
            sub.get_nowait()
        broker.publish(Event(topic="a.*.b", payload={}))  # literal match
        assert sub.get_nowait().topic == "a.*.b"


# ---------------------------------------------------------------------------
# Backpressure — bounded buffer, drop-oldest, single dedup'd overflow event
# ---------------------------------------------------------------------------


class TestBackpressure:
    """Overflow drops oldest events and emits one deduplicated core.overflow notification."""

    def test_default_buffer_size_is_256(self) -> None:
        broker = EventBroker()
        sub = broker.subscribe(["test"])
        for i in range(256):
            broker.publish(Event(topic="test", payload={"n": i}))
        assert sub.overflow_count == 0
        broker.publish(Event(topic="test", payload={"n": 256}))
        assert sub.overflow_count == 1

    def test_custom_buffer_size_respected(self) -> None:
        broker = EventBroker()
        sub = broker.subscribe(["test"], buffer_size=4)
        for i in range(4):
            broker.publish(Event(topic="test", payload={"n": i}))
        assert sub.overflow_count == 0
        broker.publish(Event(topic="test", payload={"n": 4}))
        assert sub.overflow_count == 1

    def test_drop_oldest_on_overflow(self) -> None:
        broker = EventBroker()
        sub = broker.subscribe(["test"], buffer_size=2)
        broker.publish(Event(topic="test", payload={"n": 1}))
        broker.publish(Event(topic="test", payload={"n": 2}))
        broker.publish(Event(topic="test", payload={"n": 3}))  # drops n=1
        # Drain queue; n=1 must be gone, n=2 and n=3 must be present.
        seen_n: list[int] = []
        while True:
            try:
                ev = sub.get_nowait()
            except QueueEmpty:
                break
            if ev.topic != "core.overflow":
                seen_n.append(ev.payload["n"])
        assert 1 not in seen_n
        assert 2 in seen_n
        assert 3 in seen_n

    def test_overflow_event_enqueued_on_drop(self) -> None:
        broker = EventBroker()
        sub = broker.subscribe(["test"], buffer_size=1)
        broker.publish(Event(topic="test", payload={"n": 1}))
        broker.publish(Event(topic="test", payload={"n": 2}))  # drops n=1
        events = []
        while True:
            try:
                events.append(sub.get_nowait())
            except QueueEmpty:
                break
        overflow = [e for e in events if e.topic == "core.overflow"]
        assert len(overflow) == 1
        assert overflow[0].payload["dropped_count"] >= 1
        assert overflow[0].payload["subscription_topics"] == ["test"]

    def test_overflow_event_dedup(self) -> None:
        broker = EventBroker()
        sub = broker.subscribe(["test"], buffer_size=1)
        for i in range(5):
            broker.publish(Event(topic="test", payload={"n": i}))
        # Five publishes into a 1-slot buffer: multiple drops, but exactly ONE
        # core.overflow event with a cumulative dropped_count.
        events = []
        while True:
            try:
                events.append(sub.get_nowait())
            except QueueEmpty:
                break
        overflow = [e for e in events if e.topic == "core.overflow"]
        assert len(overflow) == 1

    def test_overflow_count_resets_after_consume(self) -> None:
        broker = EventBroker()
        sub = broker.subscribe(["test"], buffer_size=1)
        broker.publish(Event(topic="test", payload={"n": 1}))
        broker.publish(Event(topic="test", payload={"n": 2}))  # overflow #1
        # Drain everything, including the overflow event.
        while True:
            try:
                sub.get_nowait()
            except QueueEmpty:
                break
        assert sub.overflow_count == 0  # reset after consume
        # Force another overflow; a fresh notification must be produced.
        broker.publish(Event(topic="test", payload={"n": 3}))
        broker.publish(Event(topic="test", payload={"n": 4}))  # overflow #2
        assert sub.overflow_count >= 1
        events = []
        while True:
            try:
                events.append(sub.get_nowait())
            except QueueEmpty:
                break
        overflow = [e for e in events if e.topic == "core.overflow"]
        assert len(overflow) == 1

    def test_slow_consumer_does_not_block_publisher(self) -> None:
        broker = EventBroker()
        sub = broker.subscribe(["test"], buffer_size=4)
        # Publisher must not block even though consumer never reads.
        for i in range(100):
            broker.publish(Event(topic="test", payload={"n": i}))
        assert sub.overflow_count > 0


# ---------------------------------------------------------------------------
# Subscription lifecycle — unsubscribe / close
# ---------------------------------------------------------------------------


class TestSubscriptionLifecycle:
    """unsubscribe() / close() stop event delivery and make the handle inert."""

    def test_unsubscribe_stops_event_delivery(self) -> None:
        broker = EventBroker()
        sub = broker.subscribe(["test"])
        broker.unsubscribe(sub)
        broker.publish(Event(topic="test", payload={}))  # publish must not raise
        with pytest.raises(SubscriptionClosedError):
            sub.get_nowait()

    def test_close_is_alias_for_unsubscribe(self) -> None:
        broker = EventBroker()
        sub = broker.subscribe(["test"])
        sub.close()
        assert sub.is_closed

    def test_double_unsubscribe_is_idempotent(self) -> None:
        broker = EventBroker()
        sub = broker.subscribe(["test"])
        broker.unsubscribe(sub)
        broker.unsubscribe(sub)  # no error
        assert sub.is_closed

    def test_broker_with_all_unsubscribed_still_publishes_noop(self) -> None:
        broker = EventBroker()
        sub = broker.subscribe(["test"])
        broker.unsubscribe(sub)
        broker.publish(Event(topic="test", payload={}))  # no error


# ---------------------------------------------------------------------------
# Concurrency — fan-out, independent buffers, async semantics
# ---------------------------------------------------------------------------


class TestConcurrency:
    """Multiple subscribers receive independent fan-out; async get() is honored."""

    def test_fan_out_to_multiple_subscribers(self) -> None:
        broker = EventBroker()
        sub_a = broker.subscribe(["test"])
        sub_b = broker.subscribe(["test"])
        broker.publish(Event(topic="test", payload={"n": 1}))
        assert sub_a.get_nowait().payload == {"n": 1}
        assert sub_b.get_nowait().payload == {"n": 1}

    def test_independent_buffers_per_subscriber(self) -> None:
        broker = EventBroker()
        sub_a = broker.subscribe(["test"], buffer_size=2)
        sub_b = broker.subscribe(["test"], buffer_size=100)
        # Overflow sub_a only; sub_b has plenty of room.
        for i in range(5):
            broker.publish(Event(topic="test", payload={"n": i}))
        assert sub_a.overflow_count > 0
        assert sub_b.overflow_count == 0

    async def test_async_get_waits_for_event(self) -> None:
        broker = EventBroker()
        sub = broker.subscribe(["test"])
        task = asyncio.create_task(sub.get())
        await asyncio.sleep(0.01)
        assert not task.done()
        broker.publish(Event(topic="test", payload={"x": 1}))
        event = await asyncio.wait_for(task, timeout=1.0)
        assert event.topic == "test"

    async def test_async_get_raises_after_close(self) -> None:
        broker = EventBroker()
        sub = broker.subscribe(["test"])
        task = asyncio.create_task(sub.get())
        await asyncio.sleep(0.01)
        sub.close()
        with pytest.raises(SubscriptionClosedError):
            await asyncio.wait_for(task, timeout=1.0)


# ---------------------------------------------------------------------------
# Edge cases — empty / unicode / duplicates / immutability
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Boundary conditions that often hide bugs."""

    def test_event_with_empty_payload_works(self) -> None:
        broker = EventBroker()
        sub = broker.subscribe(["test"])
        broker.publish(Event(topic="test", payload={}))
        assert sub.get_nowait().payload == {}

    def test_event_with_unicode_topic(self) -> None:
        broker = EventBroker()
        sub = broker.subscribe(["тест.подія"])
        broker.publish(Event(topic="тест.подія", payload={}))
        assert sub.get_nowait().topic == "тест.подія"

    def test_duplicate_topics_in_subscribe_preserved(self) -> None:
        # Decision: keep duplicates as-is (no silent dedup) — predictable
        # behavior over magical normalization.
        broker = EventBroker()
        sub = broker.subscribe(["test", "test"])
        assert sub.topics == ("test", "test")

    def test_event_is_frozen(self) -> None:
        event = Event(topic="test", payload={"x": 1})
        with pytest.raises(ValidationError):
            event.topic = "changed"
