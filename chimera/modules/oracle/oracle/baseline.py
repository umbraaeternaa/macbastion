"""Encrypted baseline store — SQLite + Fernet (§5.3, D3).

Schema (D3):
    events(id, ts, source, type, payload_json, ctx_json)
    baseline_meta(key, value)

ts/source/type are stored plaintext (queryable — "which module emits what at
which hour"); payload_json/ctx_json are Fernet tokens, encrypted at rest. The
Fernet key lives in a 0600 file beside the DB, generated on first use. Same
Fernet format as CHAFF's C implementation (interop not cross-tested — open tail).

STUB — RED slice. __init__ stores paths only; every operation that would touch
the DB raises NotImplementedError. No schema, no key, no crypto yet.
"""

from pathlib import Path
from typing import Any


class BaselineStore:
    """SQLite + Fernet baseline store. STUB (RED slice)."""

    SCHEMA_VERSION = 1

    def __init__(self, db_path: Path, key_path: Path) -> None:
        self._db_path = db_path
        self._key_path = key_path

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
        raise NotImplementedError("BaselineStore.record_event — RED slice")

    def load_event(self, event_id: int) -> dict[str, Any]:
        """Decrypt and return a stored event by row id."""
        raise NotImplementedError("BaselineStore.load_event — RED slice")

    def event_count(self) -> int:
        """Total number of recorded events."""
        raise NotImplementedError("BaselineStore.event_count — RED slice")

    def get_meta(self, key: str) -> str | None:
        """Read a baseline_meta value, or None if absent."""
        raise NotImplementedError("BaselineStore.get_meta — RED slice")

    def close(self) -> None:
        """Close the underlying connection."""
        raise NotImplementedError("BaselineStore.close — RED slice")
