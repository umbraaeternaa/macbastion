"""PULSE baseline store — encrypted SQLite + Fernet (§5.5, slice 2 / BS-1…BS-11).

RED stub: the public surface (types + signatures) is fixed; behaviour is NOT
implemented yet (raises NotImplementedError) so the failing tests are real — an
honest empty stub, never a pretending one (MANIFESTO §4). __init__ only stores
its args; it creates no DB, key, or files until GREEN.

Design (locked design-pass BS-1…BS-11):
- Mirrors oracle/baseline.py: SQLite + cryptography.Fernet, key in a 0600 file
  beside the DB, dir 0700, db 0600, check_same_thread=False + RLock.
- Schema (BS-4): buckets(id, ts TEXT plaintext, gated INTEGER plaintext,
  signals_json BLOB Fernet) + idx_buckets_ts + baseline_meta(key, value). ts and
  gated are plaintext so SQL can window + exclude BEFORE decrypt; the aggregate
  signal values live in the Fernet blob (§5 encrypt-at-rest; §8 — aggregates,
  never raw input).
- baseline() (BS-5): the 14-day rolling MEDIAN over NON-gated buckets in the
  half-open window [now-14d, now); None when no usable bucket carries the key.
- baseline_ready() (BS-8): distinct calendar days in [now-14d, now) >=
  CALIBRATION_DAYS (the 14-day cold-start gate; feeds scoring.score_and_mode).
- purge() (BS-7): drop buckets older than now-RETENTION_DAYS (kept >= the median
  window so retention can never starve the median).
- signals is an open {name: float} dict (BS-9) — the store does NOT hardcode
  MIRROR's aggregate field names (the MIRROR->PULSE aggregate event is undefined,
  gap D8).
- `now` is ALWAYS passed in as an ISO-8601 string (never datetime.now() inside),
  so the store is deterministic and hermetic; comparisons are ISO lexicographic.
"""

from __future__ import annotations

from pathlib import Path


class BaselineStore:
    """Encrypted per-minute aggregate store + 14-day rolling-median baseline."""

    SCHEMA_VERSION = 1
    RETENTION_DAYS = 14
    CALIBRATION_DAYS = 14

    def __init__(self, db_path: Path, key_path: Path) -> None:
        # RED: store args only — no DB/key/dir created until GREEN (no fake setup).
        self._db_path = db_path
        self._key_path = key_path

    def record_bucket(
        self, *, ts: str, signals: dict[str, float], gated: bool
    ) -> int:
        """Append one per-minute aggregate bucket (signals encrypted); return id."""
        raise NotImplementedError

    def baseline(self, signal_key: str, now: str) -> float | None:
        """14-day rolling median of signal_key over non-gated buckets in
        [now-14d, now); None if no usable bucket carries the key."""
        raise NotImplementedError

    def baseline_ready(self, now: str) -> bool:
        """True once >= CALIBRATION_DAYS distinct calendar days fall in
        [now-14d, now) (the 14-day cold-start gate)."""
        raise NotImplementedError

    def purge(self, now: str) -> int:
        """Delete buckets older than now-RETENTION_DAYS; return rows removed."""
        raise NotImplementedError

    def bucket_count(self) -> int:
        """Total number of stored buckets."""
        raise NotImplementedError

    def get_meta(self, key: str) -> str | None:
        """Read a baseline_meta value, or None if absent."""
        raise NotImplementedError

    def set_meta(self, key: str, value: str) -> None:
        """Upsert a baseline_meta key/value."""
        raise NotImplementedError

    def close(self) -> None:
        """Close the underlying connection."""
        raise NotImplementedError
