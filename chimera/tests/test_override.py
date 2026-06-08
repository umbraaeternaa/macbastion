"""Override-phrase store unit tests (OV-1…OV-6).

Hermetic: override.json under tmp_path. GREEN — the store is implemented; the assertions
are unchanged from RED. Pins: set->verify true, wrong phrase false, no-phrase-set false
(override unavailable until configured), persistence across reopen, file 0600, and the phrase
NEVER appears in the
file (only a salted hash).
"""

from core.override import OverrideStore


def _store(tmp_path):
    return OverrideStore(tmp_path / "override.json")


def test_unset_verify_false(tmp_path):
    assert _store(tmp_path).verify("anything") is False


def test_unset_is_set_false(tmp_path):
    assert _store(tmp_path).is_set() is False


def test_set_then_verify_true(tmp_path):
    s = _store(tmp_path)
    s.set_phrase("correct horse battery staple")
    assert s.verify("correct horse battery staple") is True
    assert s.is_set() is True


def test_wrong_phrase_false(tmp_path):
    s = _store(tmp_path)
    s.set_phrase("right")
    assert s.verify("wrong") is False


def test_persists_across_reopen(tmp_path):
    _store(tmp_path).set_phrase("remembered")
    assert OverrideStore(tmp_path / "override.json").verify("remembered") is True


def test_file_perms_0600(tmp_path):
    s = _store(tmp_path)
    s.set_phrase("x")
    assert ((tmp_path / "override.json").stat().st_mode & 0o777) == 0o600


def test_phrase_not_in_file(tmp_path):
    s = _store(tmp_path)
    s.set_phrase("supersecret")
    assert "supersecret" not in (tmp_path / "override.json").read_text()
