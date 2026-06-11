"""AuditLog — the reflex audit trail (AD-1). Core actuates reflexes autonomously
(lock the vault, start/stop obfuscation, escalate); this is the append-only, queryable
record of WHAT it did, WHEN, and the OUTCOME — so the operator can answer "why did my
vault lock?" post-hoc. RED until core/audit.py exists."""

from pathlib import Path
from typing import Any

from core.audit import AuditLog


def test_record_then_recent_returns_it(tmp_path: Any) -> None:
    log = AuditLog(tmp_path / "audit.jsonl")
    log.record(topic="tether.absent", commands=["vault.lock"], outcome="ok")
    recent = log.recent()
    assert len(recent) == 1
    entry = recent[0]
    assert entry["topic"] == "tether.absent"
    assert entry["commands"] == ["vault.lock"]
    assert entry["outcome"] == "ok"
    assert isinstance(entry["ts"], float) and entry["ts"] > 0  # stamped


def test_recent_empty_when_nothing_recorded(tmp_path: Any) -> None:
    log = AuditLog(tmp_path / "audit.jsonl")
    assert log.recent() == []  # no file yet -> empty, never raises


def test_record_appends_not_overwrites(tmp_path: Any) -> None:
    log = AuditLog(tmp_path / "audit.jsonl")
    log.record(topic="oracle.anomaly.detected", commands=["vault.lock"], outcome="ok")
    log.record(topic="tether.recovered", commands=["echo.stop"], outcome="ok")
    topics = [e["topic"] for e in log.recent()]
    assert topics == ["oracle.anomaly.detected", "tether.recovered"]  # both, in order


def test_recent_caps_to_n(tmp_path: Any) -> None:
    log = AuditLog(tmp_path / "audit.jsonl")
    for i in range(10):
        log.record(topic=f"t{i}", commands=["x"], outcome="ok")
    recent = log.recent(n=3)
    assert [e["topic"] for e in recent] == ["t7", "t8", "t9"]  # the last 3, in order


def test_record_outcome_can_capture_failure(tmp_path: Any) -> None:
    log = AuditLog(tmp_path / "audit.jsonl")
    log.record(topic="tether.absent", commands=["vault.lock"], outcome="error: module offline")
    assert "offline" in log.recent()[0]["outcome"]


def test_file_is_owner_only(tmp_path: Any) -> None:
    path = Path(tmp_path / "audit.jsonl")
    log = AuditLog(path)
    log.record(topic="t", commands=["x"], outcome="ok")
    assert (path.stat().st_mode & 0o077) == 0  # 0600 — no group/other access
