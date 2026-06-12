"""PULSE daemon client-unit — events emission (EM-1…EM-6).

Hermetic: a FakeWriter captures emitted frames; `now` is injected; the store is seeded
for baseline_ready so the mode is the real score-mode (not forced normal). No sockets,
no Ollama. GREEN — _tick is implemented; the 3 assertions are unchanged from RED.

Mode by injected now (session_start 2026-06-12T00:00, idle None, baseline_ready True):
  03:00 -> temporal 0.5*1.0 + 0.25*(3/12) = 0.5625 -> caution
  14:00 -> temporal 0.5*0.05 + 0.25*1.0 = 0.275  -> normal
"""

import json
from datetime import datetime, timedelta

from pulse.baseline import BaselineStore
from pulse.client import PulseClient

NOW_CAUTION = "2026-06-12T03:00:00"
NOW_NORMAL = "2026-06-12T14:00:00"


class FakeWriter:
    """Captures frames written by _send_cmd (no socket)."""

    def __init__(self) -> None:
        self.frames: list[str] = []

    def write(self, data) -> None:
        self.frames.append(data.decode() if isinstance(data, bytes) else data)

    async def drain(self) -> None:
        pass


def _seeded_client(tmp_path):
    store = BaselineStore(tmp_path / "baseline.db", tmp_path / "baseline.key")
    base = datetime(2026, 6, 12, 3, 0, 0)
    for d in range(1, 15):  # 14 distinct days -> baseline_ready True
        store.record_bucket(
            ts=(base - timedelta(days=d)).isoformat(), signals={"x": 1.0}, gated=False
        )
    client = PulseClient(
        tmp_path, store, session_start="2026-06-12T00:00:00",
        idle_reader=lambda: None,  # hermetic: no real ioreg, idle stays absent
    )
    client._cmd_writer = FakeWriter()
    return client


def _mode_events(client):
    return [
        json.loads(f)
        for f in client._cmd_writer.frames
        if "pulse.mode.changed" in f
    ]


async def test_first_tick_no_emit(tmp_path):
    client = _seeded_client(tmp_path)
    await client._tick(NOW_CAUTION)  # establishes _last_mode; no transition
    assert _mode_events(client) == []


async def test_tick_emits_on_mode_change(tmp_path):
    client = _seeded_client(tmp_path)
    await client._tick(NOW_CAUTION)  # establish caution
    await client._tick(NOW_NORMAL)  # caution -> normal: emit
    ev = _mode_events(client)
    assert len(ev) == 1
    p = ev[0]["params"]
    assert p["old_mode"] == "caution"
    assert p["new_mode"] == "normal"
    assert p["primary_signal"] == "temporal"
    assert 0.0 <= p["score"] <= 1.0


async def test_no_emit_when_mode_unchanged(tmp_path):
    client = _seeded_client(tmp_path)
    await client._tick(NOW_CAUTION)  # establish caution
    await client._tick(NOW_CAUTION)  # same mode: no emit
    assert _mode_events(client) == []


# -- PD-idle-2: the daemon feeds a live idle reader into the IdleTracker -------


def _idle_client(tmp_path, readings):
    """A seeded client whose idle reader yields the given readings in order."""
    store = BaselineStore(tmp_path / "baseline.db", tmp_path / "baseline.key")
    it = iter(readings)
    client = PulseClient(
        tmp_path, store, session_start="2026-06-12T00:00:00",
        idle_reader=lambda: next(it),
    )
    client._cmd_writer = FakeWriter()
    return client


async def test_daemon_feeds_idle_tracker(tmp_path):
    # away past the gap threshold, then back -> the daemon stamps last_idle_end.
    client = _idle_client(tmp_path, [400.0, 1.0])
    await client._compute("2026-06-12T10:05:00")  # idle 400s -> in a gap
    await client._compute("2026-06-12T10:06:00")  # idle 1s   -> returned, gap ends
    assert client._idle.last_idle_end == "2026-06-12T10:06:00"


async def test_idle_reader_failure_is_fail_open(tmp_path):
    # the idle sensor unavailable (None) must never crash or stamp (fail-open §8).
    client = _idle_client(tmp_path, [None, None])
    score, _mode, _ = await client._compute("2026-06-12T14:00:00")
    assert 0.0 <= score <= 1.0
    assert client._idle.last_idle_end is None
