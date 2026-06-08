"""PULSE baseline store tests (§5.5, slice 2 / BS-1…BS-11).

Hermetic: file-based SQLite under tmp_path, `now` injected as an ISO-8601 string
(no datetime.now() inside the store). GREEN — the store is implemented; the 24
assertions are unchanged from RED.
"""

from datetime import datetime, timedelta

import pytest
from pulse.baseline import BaselineStore

# A fixed reference instant; tests build timestamps relative to it.
BASE = datetime(2026, 6, 10, 12, 0, 0)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


@pytest.fixture
def paths(tmp_path):
    return tmp_path / "pulse" / "baseline.db", tmp_path / "pulse" / "baseline.key"


@pytest.fixture
def store(paths):
    return BaselineStore(*paths)


# -- construction / persistence --------------------------------------------


def test_db_file_perms_0600(store, paths):
    db, _ = paths
    assert db.exists()
    assert (db.stat().st_mode & 0o777) == 0o600


def test_key_file_perms_0600(store, paths):
    _, key = paths
    assert key.exists()
    assert (key.stat().st_mode & 0o777) == 0o600


def test_dir_perms_0700(store, paths):
    db, _ = paths
    assert (db.parent.stat().st_mode & 0o777) == 0o700


def test_schema_version_meta(store):
    assert store.get_meta("schema_version") == "1"


def test_meta_roundtrip(store):
    store.set_meta("k", "v")
    assert store.get_meta("k") == "v"


# -- record / count --------------------------------------------------------


def test_bucket_count_starts_zero(store):
    assert store.bucket_count() == 0


def test_record_increments_count(store):
    store.record_bucket(ts=_iso(BASE), signals={"s": 1.0}, gated=False)
    store.record_bucket(ts=_iso(BASE), signals={"s": 2.0}, gated=False)
    assert store.bucket_count() == 2


def test_record_returns_increasing_ids(store):
    i1 = store.record_bucket(ts=_iso(BASE), signals={"s": 1.0}, gated=False)
    i2 = store.record_bucket(ts=_iso(BASE), signals={"s": 2.0}, gated=False)
    assert i1 == 1
    assert i2 == 2


def test_signals_encrypted_at_rest(store, paths):
    db, _ = paths
    store.record_bucket(
        ts=_iso(BASE), signals={"typing_speed_secret": 1234.5}, gated=False
    )
    raw = db.read_bytes()
    assert b"typing_speed_secret" not in raw
    assert b"1234.5" not in raw


# -- baseline median -------------------------------------------------------


def test_baseline_median_odd(store):
    for i, v in enumerate([10.0, 20.0, 30.0], start=1):
        store.record_bucket(
            ts=_iso(BASE - timedelta(days=i)), signals={"s": v}, gated=False
        )
    assert store.baseline("s", _iso(BASE)) == 20.0


def test_baseline_median_even(store):
    for i, v in enumerate([10.0, 20.0, 30.0, 40.0], start=1):
        store.record_bucket(
            ts=_iso(BASE - timedelta(days=i)), signals={"s": v}, gated=False
        )
    assert store.baseline("s", _iso(BASE)) == 25.0


def test_baseline_per_signal_key(store):
    store.record_bucket(
        ts=_iso(BASE - timedelta(days=1)), signals={"a": 10.0, "b": 100.0}, gated=False
    )
    store.record_bucket(
        ts=_iso(BASE - timedelta(days=2)), signals={"a": 20.0, "b": 200.0}, gated=False
    )
    assert store.baseline("a", _iso(BASE)) == 15.0
    assert store.baseline("b", _iso(BASE)) == 150.0


def test_baseline_skips_buckets_without_key(store):
    store.record_bucket(
        ts=_iso(BASE - timedelta(days=1)), signals={"s": 10.0}, gated=False
    )
    store.record_bucket(
        ts=_iso(BASE - timedelta(days=2)), signals={"other": 999.0}, gated=False
    )
    assert store.baseline("s", _iso(BASE)) == 10.0


def test_baseline_excludes_gated(store):
    for i, v in enumerate([10.0, 20.0, 30.0], start=1):
        store.record_bucket(
            ts=_iso(BASE - timedelta(days=i)), signals={"s": v}, gated=False
        )
    store.record_bucket(
        ts=_iso(BASE - timedelta(hours=1)), signals={"s": 1000.0}, gated=True
    )
    assert store.baseline("s", _iso(BASE)) == 20.0


def test_baseline_none_when_empty(store):
    assert store.baseline("s", _iso(BASE)) is None


def test_baseline_none_when_all_gated(store):
    store.record_bucket(
        ts=_iso(BASE - timedelta(days=1)), signals={"s": 1.0}, gated=True
    )
    assert store.baseline("s", _iso(BASE)) is None


def test_baseline_none_when_key_absent(store):
    store.record_bucket(
        ts=_iso(BASE - timedelta(days=1)), signals={"other": 1.0}, gated=False
    )
    assert store.baseline("s", _iso(BASE)) is None


# -- window boundaries (half-open [now-14d, now)) --------------------------


def test_baseline_half_open_window(store):
    now = datetime(2026, 6, 20, 12, 0, 0)
    cutoff = now - timedelta(days=14)
    store.record_bucket(ts=_iso(cutoff), signals={"s": 100.0}, gated=False)  # included
    store.record_bucket(ts=_iso(now), signals={"s": 999.0}, gated=False)  # excluded (==now)
    store.record_bucket(
        ts=_iso(cutoff - timedelta(seconds=1)), signals={"s": 1.0}, gated=False
    )  # excluded (too old)
    assert store.baseline("s", _iso(now)) == 100.0


def test_baseline_excludes_outside_window(store):
    now = datetime(2026, 6, 20, 12, 0, 0)
    store.record_bucket(
        ts=_iso(now - timedelta(days=20)), signals={"s": 999.0}, gated=False
    )
    store.record_bucket(
        ts=_iso(now - timedelta(days=5)), signals={"s": 10.0}, gated=False
    )
    assert store.baseline("s", _iso(now)) == 10.0


# -- retention purge -------------------------------------------------------


def test_purge_removes_old(store):
    now = datetime(2026, 6, 20, 12, 0, 0)
    store.record_bucket(
        ts=_iso(now - timedelta(days=20)), signals={"s": 1.0}, gated=False
    )
    store.record_bucket(
        ts=_iso(now - timedelta(days=5)), signals={"s": 2.0}, gated=False
    )
    removed = store.purge(_iso(now))
    assert removed == 1
    assert store.bucket_count() == 1


def test_purge_keeps_boundary(store):
    now = datetime(2026, 6, 20, 12, 0, 0)
    cutoff = now - timedelta(days=14)
    store.record_bucket(ts=_iso(cutoff), signals={"s": 1.0}, gated=False)  # kept (>=)
    store.record_bucket(
        ts=_iso(cutoff - timedelta(seconds=1)), signals={"s": 2.0}, gated=False
    )  # deleted
    removed = store.purge(_iso(now))
    assert removed == 1
    assert store.bucket_count() == 1


# -- baseline_ready (14-day cold-start) ------------------------------------


def test_baseline_ready_false_below_14_days(store):
    now = datetime(2026, 6, 20, 12, 0, 0)
    for d in range(1, 14):  # 13 distinct days in [now-14d, now)
        store.record_bucket(
            ts=_iso(now - timedelta(days=d)), signals={"s": 1.0}, gated=False
        )
    assert store.baseline_ready(_iso(now)) is False


def test_baseline_ready_true_at_14_days(store):
    now = datetime(2026, 6, 20, 12, 0, 0)
    for d in range(1, 15):  # 14 distinct days, all in [now-14d, now)
        store.record_bucket(
            ts=_iso(now - timedelta(days=d)), signals={"s": 1.0}, gated=False
        )
    assert store.baseline_ready(_iso(now)) is True


def test_baseline_ready_false_when_empty(store):
    assert store.baseline_ready(_iso(BASE)) is False
