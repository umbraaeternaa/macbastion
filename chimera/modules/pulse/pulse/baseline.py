"""PULSE baseline store — encrypted SQLite + Fernet (§5.5, slice 2 / BS-1…BS-11).

Stores per-minute aggregate buckets and computes the operator's 14-day rolling-
median baseline. Mirrors oracle/baseline.py (SQLite + cryptography.Fernet).

Design (locked design-pass BS-1…BS-11):
- Schema (BS-4): buckets(id, ts TEXT plaintext, gated INTEGER plaintext,
  signals_json BLOB Fernet) + idx_buckets_ts + baseline_meta(key, value). ts and
  gated are plaintext so SQL windows + excludes BEFORE decrypt; the aggregate
  signal VALUES live in the Fernet blob (§5 encrypt-at-rest; §8 — aggregates,
  never raw input).
- baseline() (BS-5): the 14-day rolling MEDIAN over NON-gated buckets in the
  half-open window [now-14d, now); None when no usable bucket carries the key.
- baseline_ready() (BS-8): >= CALIBRATION_DAYS distinct calendar days in
  [now-14d, now) — the 14-day cold-start gate (feeds scoring.score_and_mode).
- purge() (BS-7): drop buckets older than now-RETENTION_DAYS (kept >= the median
  window so retention never starves the median).
- signals is an open {name: float} dict (BS-9) — no MIRROR field names hardcoded
  (the MIRROR->PULSE aggregate event is undefined, gap D8).
- `now` is ALWAYS an ISO-8601 string (never datetime.now() inside); comparisons
  are ISO lexicographic (fixed-width, zero-padded -> chronological order).
"""

from __future__ import annotations

import json
import sqlite3
import statistics
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet

_SCHEMA = """
CREATE TABLE IF NOT EXISTS buckets (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           TEXT NOT NULL,
    gated        INTEGER NOT NULL,
    signals_json BLOB NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_buckets_ts ON buckets(ts);
CREATE TABLE IF NOT EXISTS baseline_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class BaselineStore:
    """Encrypted per-minute aggregate store + 14-day rolling-median baseline."""

    SCHEMA_VERSION = 1
    RETENTION_DAYS = 14
    CALIBRATION_DAYS = 14

    def __init__(self, db_path: Path, key_path: Path) -> None:
        self._db_path = db_path
        self._key_path = key_path
        db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._fernet = Fernet(self._load_or_create_key())
        # check_same_thread=False + RLock: the daemon will wrap store calls in
        # asyncio.to_thread (like ORACLE), so the single connection is reached
        # from both the loop thread and the executor thread; the lock serializes.
        self._lock = threading.RLock()
        self._con = sqlite3.connect(db_path, check_same_thread=False)
        self._con.row_factory = sqlite3.Row
        self._con.executescript(_SCHEMA)
        self._con.commit()
        db_path.chmod(0o600)
        self.set_meta("schema_version", str(self.SCHEMA_VERSION))

    # -- key management ---------------------------------------------------

    def _load_or_create_key(self) -> bytes:
        """Load the Fernet key, generating a 0600 key file on first use."""
        if self._key_path.exists():
            return self._key_path.read_bytes()
        self._key_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        key = Fernet.generate_key()
        # Create empty 0600 before writing so the key never lands world-readable.
        self._key_path.touch(mode=0o600, exist_ok=True)
        self._key_path.chmod(0o600)
        self._key_path.write_bytes(key)
        return key

    # -- buckets ----------------------------------------------------------

    def record_bucket(
        self, *, ts: str, signals: dict[str, float], gated: bool
    ) -> int:
        """Append one per-minute aggregate bucket (signals encrypted); return id."""
        blob = self._fernet.encrypt(json.dumps(signals).encode())
        with self._lock:
            cur = self._con.execute(
                "INSERT INTO buckets (ts, gated, signals_json) VALUES (?, ?, ?)",
                (ts, 1 if gated else 0, blob),
            )
            self._con.commit()
            row_id = cur.lastrowid
        assert row_id is not None  # AUTOINCREMENT always yields a rowid
        return row_id

    def baseline(self, signal_key: str, now: str) -> float | None:
        """14-day rolling median of signal_key over non-gated buckets in
        [now-14d, now); None if no usable bucket carries the key."""
        cutoff = self._cutoff(now)
        with self._lock:
            rows = self._con.execute(
                "SELECT signals_json FROM buckets "
                "WHERE ts >= ? AND ts < ? AND gated = 0",
                (cutoff, now),
            ).fetchall()
        values: list[float] = []
        for row in rows:
            signals: dict[str, Any] = json.loads(
                self._fernet.decrypt(row["signals_json"])
            )
            if signal_key in signals:
                values.append(float(signals[signal_key]))
        return statistics.median(values) if values else None

    def baseline_ready(self, now: str) -> bool:
        """True once >= CALIBRATION_DAYS distinct calendar days fall in
        [now-14d, now) (the 14-day cold-start gate)."""
        return self.calibration_days(now) >= self.CALIBRATION_DAYS

    def purge(self, now: str) -> int:
        """Delete buckets older than now-RETENTION_DAYS; return rows removed."""
        cutoff = self._cutoff(now)
        with self._lock:
            cur = self._con.execute("DELETE FROM buckets WHERE ts < ?", (cutoff,))
            self._con.commit()
            return cur.rowcount

    def bucket_count(self) -> int:
        """Total number of stored buckets."""
        with self._lock:
            row = self._con.execute("SELECT COUNT(*) AS n FROM buckets").fetchone()
        return int(row["n"])

    def calibration_days(self, now: str) -> int:
        """Distinct calendar days observed in [now-14d, now) (calibration progress)."""
        cutoff = self._cutoff(now)
        with self._lock:
            row = self._con.execute(
                "SELECT COUNT(DISTINCT substr(ts, 1, 10)) AS n FROM buckets "
                "WHERE ts >= ? AND ts < ?",
                (cutoff, now),
            ).fetchone()
        return int(row["n"])

    def clear(self) -> int:
        """Delete ALL buckets (calibration reset); return rows removed."""
        with self._lock:
            cur = self._con.execute("DELETE FROM buckets")
            self._con.commit()
            return cur.rowcount

    # -- meta -------------------------------------------------------------

    def get_meta(self, key: str) -> str | None:
        """Read a baseline_meta value, or None if absent."""
        with self._lock:
            row = self._con.execute(
                "SELECT value FROM baseline_meta WHERE key = ?", (key,)
            ).fetchone()
        return None if row is None else str(row["value"])

    def set_meta(self, key: str, value: str) -> None:
        """Upsert a baseline_meta key/value."""
        with self._lock:
            self._con.execute(
                "INSERT INTO baseline_meta (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
            self._con.commit()

    def close(self) -> None:
        """Close the underlying connection."""
        with self._lock:
            self._con.close()

    # -- helpers ----------------------------------------------------------

    def _cutoff(self, now: str) -> str:
        """now - RETENTION_DAYS as an ISO string (the retention/median cutoff)."""
        cut = datetime.fromisoformat(now) - timedelta(days=self.RETENTION_DAYS)
        return cut.isoformat()
