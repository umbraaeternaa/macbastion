"""PULSE daemon client-unit — events emission (EM-1…EM-6).

Hermetic: a FakeWriter captures emitted frames; `now` is injected; the store is seeded
for baseline_ready so the mode is the real score-mode (not forced normal). No sockets,
no Ollama. RED — _tick raises NotImplementedError until GREEN.

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
    client = PulseClient(tmp_path, store, session_start="2026-06-12T00:00:00")
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
