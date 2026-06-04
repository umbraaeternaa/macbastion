"""Unit: BaselineStore — SQLite + Fernet (§5.3, D3).

RED slice: these fail against the stub (record/load/count/get_meta raise
NotImplementedError; no schema, no key file). No core, no Ollama.
"""

import sqlite3
import stat

import pytest
from cryptography.fernet import InvalidToken

from oracle.baseline import BaselineStore


def _store(tmp_path):
    return BaselineStore(tmp_path / "baseline.db", tmp_path / "baseline.key")


def test_record_and_load_roundtrip(tmp_path):
    store = _store(tmp_path)
    rid = store.record_event(
        ts="2026-06-04T12:00:00Z",
        source="chaff",
        event_type="request.sent",
        payload={"url": "https://example", "gap_ms": 1200},
    )
    loaded = store.load_event(rid)
    assert loaded["source"] == "chaff"
    assert loaded["type"] == "request.sent"
    assert loaded["payload"]["url"] == "https://example"


def test_context_optional_roundtrip(tmp_path):
    store = _store(tmp_path)
    rid = store.record_event(
        ts="2026-06-04T12:00:00Z",
        source="chaff",
        event_type="request.sent",
        payload={"url": "https://example"},
        context={"modules_up": ["chaff"]},
    )
    loaded = store.load_event(rid)
    assert loaded["context"]["modules_up"] == ["chaff"]


def test_event_count_increments(tmp_path):
    store = _store(tmp_path)
    assert store.event_count() == 0
    store.record_event(ts="t", source="chaff", event_type="request.sent", payload={})
    store.record_event(ts="t", source="chaff", event_type="error", payload={})
    assert store.event_count() == 2


def test_schema_has_events_and_meta_tables(tmp_path):
    store = _store(tmp_path)
    store.record_event(ts="t", source="chaff", event_type="request.sent", payload={})
    con = sqlite3.connect(tmp_path / "baseline.db")
    try:
        names = {
            row[0]
            for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    finally:
        con.close()
    assert {"events", "baseline_meta"} <= names


def test_payload_encrypted_at_rest(tmp_path):
    store = _store(tmp_path)
    store.record_event(
        ts="t",
        source="chaff",
        event_type="request.sent",
        payload={"secret": "topsecret-marker"},
    )
    raw = (tmp_path / "baseline.db").read_bytes()
    assert b"topsecret-marker" not in raw  # Fernet token, not plaintext


def test_tampered_token_raises(tmp_path):
    store = _store(tmp_path)
    rid = store.record_event(
        ts="t", source="chaff", event_type="request.sent", payload={"a": 1}
    )
    con = sqlite3.connect(tmp_path / "baseline.db")
    try:
        con.execute(
            "UPDATE events SET payload_json = ? WHERE id = ?", (b"tampered", rid)
        )
        con.commit()
    finally:
        con.close()
    with pytest.raises(InvalidToken):
        store.load_event(rid)


def test_key_file_mode_0600(tmp_path):
    key_path = tmp_path / "baseline.key"
    BaselineStore(tmp_path / "baseline.db", key_path)
    assert key_path.exists()
    assert stat.S_IMODE(key_path.stat().st_mode) == 0o600


def test_get_meta_schema_version(tmp_path):
    store = _store(tmp_path)
    assert store.get_meta("schema_version") == str(BaselineStore.SCHEMA_VERSION)
