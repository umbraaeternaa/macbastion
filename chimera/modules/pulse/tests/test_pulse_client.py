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


# -- PD-A-2: the daemon feeds MIRROR's group-A aggregates into assess --------


def _client_with_error_baseline(tmp_path):
    """A baseline-ready client whose 14-day baseline holds error_rate ~0.05."""
    store = BaselineStore(tmp_path / "baseline.db", tmp_path / "baseline.key")
    base = datetime(2026, 6, 12, 3, 0, 0)
    for d in range(1, 15):
        store.record_bucket(
            ts=(base - timedelta(days=d)).isoformat(),
            signals={"error_rate": 0.05}, gated=False,
        )
    client = PulseClient(
        tmp_path, store, session_start="2026-06-12T00:00:00", idle_reader=lambda: None
    )
    client._cmd_writer = FakeWriter()
    return client


async def test_ingested_input_raises_fatigue(tmp_path):
    client = _client_with_error_baseline(tmp_path)
    base_score, _, _ = await client._compute(NOW_NORMAL)  # no input -> temporal only
    client._on_input_aggregates(chars=100, deletes=30, mouse_path_ratio=None)  # 0.3 >> 0.05
    fat_score, _, _ = await client._compute(NOW_NORMAL)
    assert fat_score > base_score  # group-A error_rate fatigue raised the score


async def test_idle_minute_keeps_group_a_absent(tmp_path):
    client = _client_with_error_baseline(tmp_path)
    base_score, _, _ = await client._compute(NOW_NORMAL)
    client._on_input_aggregates(chars=0, deletes=0, mouse_path_ratio=None)  # a quiet minute
    quiet_score, _, _ = await client._compute(NOW_NORMAL)
    assert quiet_score == base_score  # no typing -> group A absent, no fake fatigue


# -- PD-A-3: PULSE subscribes to MIRROR's per-minute input-aggregate event ----


def test_subscribes_to_mirror_input_event():
    assert "mirror.input.minute" in PulseClient.SUBSCRIBE_TOPICS


async def test_input_event_feeds_group_a(tmp_path):
    client = _seeded_client(tmp_path)
    frame = json.dumps({
        "jsonrpc": "2.0", "method": "mirror.input.minute",
        "params": {"chars": 100, "deletes": 30, "mouse_path_ratio": None},
    })
    await client._on_event_frame(frame)
    assert client._group_a == {"typing_speed": 100.0, "error_rate": 0.3}


async def test_unrelated_event_leaves_group_a_untouched(tmp_path):
    client = _seeded_client(tmp_path)
    frame = json.dumps({
        "jsonrpc": "2.0", "method": "mirror.profile.changed",
        "params": {"profile": "heavy"},
    })
    await client._on_event_frame(frame)
    assert client._group_a is None  # an unrelated event never touches group-A


# -- PD-C-2: PULSE consumes ORACLE's anomaly as the group-C drift signal -----


def test_subscribes_to_oracle_anomaly():
    assert "oracle.anomaly.detected" in PulseClient.SUBSCRIBE_TOPICS


async def test_anomaly_event_feeds_drift_tracker(tmp_path):
    client = _seeded_client(tmp_path)
    frame = json.dumps({
        "jsonrpc": "2.0", "method": "oracle.anomaly.detected", "params": {"score": 0.8},
    })
    await client._on_event_frame(frame)
    # queried right after the observe -> within the window -> the score is the drift
    assert client._drift.drift(datetime.now().isoformat()) == 0.8


async def test_compute_folds_in_drift(tmp_path):
    client = _seeded_client(tmp_path)
    base_score, _, _ = await client._compute(NOW_NORMAL)  # no drift
    client._drift.observe(NOW_NORMAL, 0.9)  # a fresh ORACLE anomaly
    drift_score, _, _ = await client._compute(NOW_NORMAL)
    assert drift_score > base_score  # group-C drift raised the fatigue score


# -- §9: chronotype is LEARNED from observed activity, not configured ---------


async def test_active_minute_records_and_persists_activity(tmp_path):
    # idle below the active threshold -> the tick counts as one active minute at that hour.
    client = _idle_client(tmp_path, [10.0])
    await client._compute("2026-06-12T03:30:00")  # hour 3, idle 10s < 300 -> active
    assert client._activity_hist[3] == 1
    assert json.loads(client._store.get_meta("activity_hist"))[3] == 1  # persisted


async def test_idle_minute_records_no_activity(tmp_path):
    # idle past the active threshold -> not present -> no activity counted.
    client = _idle_client(tmp_path, [400.0])
    await client._compute("2026-06-12T03:30:00")
    assert sum(client._activity_hist) == 0


async def test_activity_histogram_persists_across_restart(tmp_path):
    store = BaselineStore(tmp_path / "baseline.db", tmp_path / "baseline.key")
    c1 = PulseClient(tmp_path, store, idle_reader=lambda: None)
    c1._activity_hist[2] = 5
    await c1._observe_activity("2026-06-12T02:10:00")  # hour 2 -> 6, persisted
    c2 = PulseClient(tmp_path, store, idle_reader=lambda: None)  # reload over same store
    assert c2._activity_hist[2] == 6


async def test_effective_chronotype_honors_config_until_saturated(tmp_path):
    store = BaselineStore(tmp_path / "baseline.db", tmp_path / "baseline.key")
    client = PulseClient(tmp_path, store, chronotype="night_owl", idle_reader=lambda: None)
    assert client._effective_chronotype() == "night_owl"  # cold-start: honor explicit config
    client._activity_hist[14] = 700  # saturated, day-heavy -> learned typical overrides config
    assert client._effective_chronotype() == "typical"


async def test_learned_night_owl_dampens_night_fatigue(tmp_path):
    client = _seeded_client(tmp_path)
    typical_score, _, _ = await client._compute(NOW_CAUTION)  # 03:00, empty hist -> typical
    client._activity_hist[3] = 700  # saturated night activity -> learned night_owl
    owl_score, _, _ = await client._compute(NOW_CAUTION)
    assert owl_score < typical_score  # night_owl x0.4 on the 3am hour weight
