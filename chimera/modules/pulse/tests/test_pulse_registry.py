"""PULSE danger-registry unit tests (DR-1…DR-6).

Hermetic: registry.json under tmp_path. RED — the registry methods raise
NotImplementedError until GREEN. Pins: §4 defaults seeded on first use, add idempotent
(no dupes), remove idempotent (no error if absent), persistence across reopen, file 0600.
"""

from pulse.registry import DEFAULT_DANGERS, DangerRegistry


def _reg(tmp_path):
    return DangerRegistry(tmp_path / "registry.json")


def test_seeds_defaults_on_first_use(tmp_path):
    assert _reg(tmp_path).list() == DEFAULT_DANGERS


def test_add_appends_and_dedupes(tmp_path):
    r = _reg(tmp_path)
    r.add("custom:thing")
    assert "custom:thing" in r.list()
    n = len(r.list())
    r.add("custom:thing")  # idempotent — no duplicate
    assert len(r.list()) == n


def test_remove_idempotent(tmp_path):
    r = _reg(tmp_path)
    r.add("custom:thing")
    r.remove("custom:thing")
    assert "custom:thing" not in r.list()
    r.remove("custom:thing")  # absent -> no error
    assert "custom:thing" not in r.list()


def test_persists_across_reopen(tmp_path):
    _reg(tmp_path).add("persist:me")
    reopened = DangerRegistry(tmp_path / "registry.json")
    assert "persist:me" in reopened.list()


def test_file_perms_0600(tmp_path):
    r = _reg(tmp_path)
    r.add("x")  # force a write
    assert ((tmp_path / "registry.json").stat().st_mode & 0o777) == 0o600
