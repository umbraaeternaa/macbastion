"""PULSE §6 finishers — calibrate + pulse.error (PF-1…PF-7).

Hermetic: store-level (calibration_days / clear) + client-level (calibrate handlers and
the pulse.error tick-channel) with a FakeWriter capturing emitted frames. RED — the store
methods, the calibrate handlers, and _safe_tick raise NotImplementedError until GREEN.
"""

import json

from pulse.baseline import BaselineStore
from pulse.client import PulseClient

NOW = "2026-06-12T12:00:00"


class FakeWriter:
    def __init__(self) -> None:
        self.frames: list[str] = []

    def write(self, data) -> None:
        self.frames.append(data.decode() if isinstance(data, bytes) else data)

    async def drain(self) -> None:
        pass


def _client(tmp_path, store=None):
    store = store or BaselineStore(tmp_path / "b.db", tmp_path / "b.key")
    c = PulseClient(tmp_path, store, session_start="2026-06-12T00:00:00")
    c._cmd_writer = FakeWriter()
    return c, store


# -- store -----------------------------------------------------------------


def test_calibration_days_counts_distinct(tmp_path):
    s = BaselineStore(tmp_path / "b.db", tmp_path / "b.key")
    for day in ("2026-06-10", "2026-06-11", "2026-06-12"):
        for hh in (9, 10):  # two buckets/day -> still one distinct day
            s.record_bucket(ts=f"{day}T{hh:02d}:00:00", signals={"x": 1.0}, gated=False)
    assert s.calibration_days(NOW) == 3


def test_clear_empties_store(tmp_path):
    s = BaselineStore(tmp_path / "b.db", tmp_path / "b.key")
    s.record_bucket(ts="2026-06-12T09:00:00", signals={"x": 1.0}, gated=False)
    s.record_bucket(ts="2026-06-12T10:00:00", signals={"x": 1.0}, gated=False)
    assert s.bucket_count() == 2
    assert s.clear() == 2
    assert s.bucket_count() == 0


# -- calibrate handlers ----------------------------------------------------


async def test_calibrate_start_reports_status(tmp_path):
    c, _ = _client(tmp_path)
    r = await c._handle_calibrate_start()
    assert r["days_required"] == 14
    assert r["days_observed"] == 0  # empty store
    assert r["ready"] is False
    assert isinstance(r["started_at"], str) and r["started_at"]


async def test_calibrate_reset_clears(tmp_path):
    store = BaselineStore(tmp_path / "b.db", tmp_path / "b.key")
    store.record_bucket(ts="2026-06-12T09:00:00", signals={"x": 1.0}, gated=False)
    c, store = _client(tmp_path, store)
    r = await c._handle_calibrate_reset()
    assert r["ok"] is True
    assert r["days_observed"] == 0
    assert store.bucket_count() == 0


# -- pulse.error tick channel ----------------------------------------------


def _errors(c):
    return [json.loads(f) for f in c._cmd_writer.frames if "pulse.error" in f]


async def test_pulse_error_on_tick_failure(tmp_path, monkeypatch):
    c, _ = _client(tmp_path)

    async def boom(now):
        raise RuntimeError("compute exploded")

    monkeypatch.setattr(c, "_compute", boom)
    await c._safe_tick("2026-06-12T03:00:00")  # must NOT raise — it announces instead
    ev = _errors(c)
    assert len(ev) == 1
    assert ev[0]["params"]["where"] == "tick"
    assert "exploded" in ev[0]["params"]["message"]
