"""Pub/sub event broker (§6.6 + §6.8 backpressure)."""

import asyncio
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict


class SubscriptionClosedError(Exception):
    """Raised when an operation is attempted on a closed subscription."""


class Event(BaseModel):
    """An event with a topic and arbitrary JSON-shaped payload (immutable)."""

    model_config = ConfigDict(frozen=True)

    topic: str
    payload: dict[str, Any]


def _matches(pattern: str, topic: str) -> bool:
    """Match a single topic against a subscription pattern.

    Recognized wildcard forms (§6.6): prefix.*, *.suffix, and bare *.
    Anything else — including internal wildcards like 'a.*.b' — is treated
    as a literal exact-match string. The "no internal *" guard in each
    arm enforces that.
    """
    if pattern == "*":
        return True
    if pattern == topic:
        return True
    if pattern.endswith(".*") and "*" not in pattern[:-2]:
        prefix = pattern[:-2]
        return topic.startswith(prefix + ".")
    if pattern.startswith("*.") and "*" not in pattern[2:]:
        suffix = pattern[2:]
        return topic.endswith("." + suffix)
    return False


class Subscription:
    """Handle for a topic subscription on an EventBroker."""

    def __init__(self, topics: tuple[str, ...], buffer_size: int) -> None:
        self._topics: tuple[str, ...] = topics
        self._queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=buffer_size)
        # Overflow event sits in a separate slot — does NOT compete with normal
        # events for the bounded buffer's capacity (Strategy B from design).
        self._overflow_pending: Event | None = None
        self._overflow_count: int = 0
        self._closed: bool = False
        self._closed_event: asyncio.Event = asyncio.Event()

    @property
    def topics(self) -> tuple[str, ...]:
        return self._topics

    @property
    def overflow_count(self) -> int:
        return self._overflow_count

    @property
    def is_closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        """Close the subscription. Idempotent. Wakes any awaiting get()."""
        if self._closed:
            return
        self._closed = True
        self._closed_event.set()

    def get_nowait(self) -> Event:
        """Return the next event, preferring the overflow slot."""
        if self._closed:
            raise SubscriptionClosedError("subscription is closed")
        if self._overflow_pending is not None:
            return self._consume_overflow()
        return self._queue.get_nowait()  # may raise asyncio.QueueEmpty

    async def get(self) -> Event:
        """Await the next event. Raises SubscriptionClosedError if closed."""
        if self._closed:
            raise SubscriptionClosedError("subscription is closed")
        if self._overflow_pending is not None:
            return self._consume_overflow()

        get_task = asyncio.ensure_future(self._queue.get())
        close_task = asyncio.ensure_future(self._closed_event.wait())
        try:
            done, pending = await asyncio.wait(
                {get_task, close_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
        finally:
            for task in (get_task, close_task):
                if not task.done():
                    task.cancel()

        if close_task in done:
            raise SubscriptionClosedError("subscription is closed")
        return get_task.result()

    def _consume_overflow(self) -> Event:
        """Return the pending overflow event and reset dedup state."""
        assert self._overflow_pending is not None
        event = self._overflow_pending
        self._overflow_pending = None
        self._overflow_count = 0
        return event

    def _try_enqueue(self, event: Event) -> None:
        """Enqueue an event; drop oldest on overflow and account for it."""
        if self._closed:
            return
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            # Buffer is full: drop the oldest regular event to make room.
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                pass  # defensive; should not happen if QueueFull just fired
            self._queue.put_nowait(event)
            self._overflow_count += 1
            self._materialize_overflow_event()

    def _materialize_overflow_event(self) -> None:
        """Create the overflow notification if none is pending (dedup)."""
        if self._overflow_pending is not None:
            return
        self._overflow_pending = Event(
            topic="core.overflow",
            payload={
                "dropped_count": self._overflow_count,
                "subscription_topics": list(self._topics),
            },
        )


class EventBroker:
    """In-memory pub/sub broker (§6.6 + §6.8 backpressure).

    Fan-out: publish() delivers each event synchronously to every matching
    subscriber's bounded buffer. Slow consumers cannot block fast publishers
    — their buffer drops oldest and a single core.overflow notification is
    surfaced once consumed.
    """

    DEFAULT_BUFFER_SIZE: ClassVar[int] = 256

    def __init__(self, default_buffer_size: int = 256) -> None:
        self._default_buffer_size: int = default_buffer_size
        self._subscriptions: set[Subscription] = set()

    def subscribe(
        self,
        topics: list[str],
        buffer_size: int | None = None,
    ) -> Subscription:
        if not topics:
            raise ValueError("must subscribe to at least one topic")
        size = buffer_size if buffer_size is not None else self._default_buffer_size
        sub = Subscription(topics=tuple(topics), buffer_size=size)
        self._subscriptions.add(sub)
        return sub

    def unsubscribe(self, sub: Subscription) -> None:
        sub.close()
        self._subscriptions.discard(sub)

    def publish(self, event: Event) -> None:
        # Snapshot via list() so a subscriber closing during fan-out cannot
        # mutate the set while we iterate.
        for sub in list(self._subscriptions):
            if sub.is_closed:
                continue
            if any(_matches(p, event.topic) for p in sub.topics):
                sub._try_enqueue(event)
