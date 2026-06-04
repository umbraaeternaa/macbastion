"""Encrypted baseline store — SQLite + Fernet (§5.3, D3).

Schema (D3):
    events(id, ts, source, type, payload_json, ctx_json)
    baseline_meta(key, value)

ts/source/type are stored plaintext (queryable — "which module emits what at
which hour"); payload_json/ctx_json are Fernet tokens, encrypted at rest. The
Fernet key lives in a 0600 file beside the DB, generated on first use. Same
Fernet format as CHAFF's C implementation (interop not cross-tested — open tail).

Synchronous and blocking by design: SQLite calls are wrapped in
asyncio.to_thread by the client (D0), keeping this module loop-agnostic.
"""

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           TEXT NOT NULL,
    source       TEXT NOT NULL,
    type         TEXT NOT NULL,
    payload_json BLOB NOT NULL,
    ctx_json     BLOB
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
CREATE TABLE IF NOT EXISTS baseline_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class BaselineStore:
    """SQLite + Fernet baseline store (§5.3, D3)."""

    SCHEMA_VERSION = 1

    def __init__(self, db_path: Path, key_path: Path) -> None:
        self._db_path = db_path
        self._key_path = key_path
        db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._fernet = Fernet(self._load_or_create_key())
        # check_same_thread=False + RLock: the client wraps store calls in
        # asyncio.to_thread (D0), so the single connection is reached from the
        # loop thread and the executor thread; the lock serializes access.
        self._lock = threading.RLock()
        self._con = sqlite3.connect(db_path, check_same_thread=False)
        self._con.row_factory = sqlite3.Row
        self._con.executescript(_SCHEMA)
        self._con.commit()
        db_path.chmod(0o600)
        self.set_meta("schema_version", str(self.SCHEMA_VERSION))
        if self.get_meta("event_count") is None:
            self.set_meta("event_count", "0")

    # -- key management ---------------------------------------------------

    def _load_or_create_key(self) -> bytes:
        """Load the Fernet key, generating a 0600 key file on first use."""
        if self._key_path.exists():
            return self._key_path.read_bytes()
        self._key_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        key = Fernet.generate_key()
        # Create empty with 0600 before writing, so the key never lands in a
        # world-readable file even briefly.
        self._key_path.touch(mode=0o600, exist_ok=True)
        self._key_path.chmod(0o600)
        self._key_path.write_bytes(key)
        return key

    # -- events -----------------------------------------------------------

    def record_event(
        self,
        *,
        ts: str,
        source: str,
        event_type: str,
        payload: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> int:
        """Append one event (encrypting payload/context); return its row id."""
        payload_token = self._fernet.encrypt(json.dumps(payload).encode())
        ctx_token = (
            self._fernet.encrypt(json.dumps(context).encode())
            if context is not None
            else None
        )
        with self._lock:
            cur = self._con.execute(
                "INSERT INTO events (ts, source, type, payload_json, ctx_json) "
                "VALUES (?, ?, ?, ?, ?)",
                (ts, source, event_type, payload_token, ctx_token),
            )
            self.set_meta("event_count", str(self.event_count() + 1))
            self._con.commit()
            row_id = cur.lastrowid
        assert row_id is not None  # AUTOINCREMENT always yields a rowid
        return row_id

    def load_event(self, event_id: int) -> dict[str, Any]:
        """Decrypt and return a stored event by row id.

        Raises cryptography.fernet.InvalidToken on a tampered ciphertext.
        """
        with self._lock:
            row = self._con.execute(
                "SELECT ts, source, type, payload_json, ctx_json FROM events "
                "WHERE id = ?",
                (event_id,),
            ).fetchone()
        if row is None:
            raise KeyError(event_id)
        payload = json.loads(self._fernet.decrypt(row["payload_json"]))
        context = (
            json.loads(self._fernet.decrypt(row["ctx_json"]))
            if row["ctx_json"] is not None
            else None
        )
        return {
            "ts": row["ts"],
            "source": row["source"],
            "type": row["type"],
            "payload": payload,
            "context": context,
        }

    def event_count(self) -> int:
        """Total number of recorded events (from baseline_meta)."""
        value = self.get_meta("event_count")
        return int(value) if value is not None else 0

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
