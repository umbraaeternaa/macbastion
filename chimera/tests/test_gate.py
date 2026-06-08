"""Cognitive gate decision unit tests (GE-1…GE-5).

Pure, hermetic. GREEN — decide() is implemented; the 8 assertions are unchanged from RED.
Pins §4 friction
(normal->allow, caution->confirm, tired->delay, exhausted->block), §8 fail-OPEN
(unknown/None mode -> allow), and the override escape (exhausted + override_ok -> allow).
"""

from core.gate import ALLOW, BLOCK, CONFIRM, DELAY, TIRED_DELAY_S, decide

DANGER = {"purge.trigger", "rm:$HOME"}
SAFE = "ls:home"
ACT = "purge.trigger"


def test_non_danger_action_always_allowed():
    assert decide(SAFE, "exhausted", DANGER).decision == ALLOW


def test_normal_allows_danger():
    assert decide(ACT, "normal", DANGER).decision == ALLOW


def test_caution_confirms():
    assert decide(ACT, "caution", DANGER).decision == CONFIRM


def test_tired_delays():
    d = decide(ACT, "tired", DANGER)
    assert d.decision == DELAY
    assert d.delay_seconds == TIRED_DELAY_S


def test_exhausted_blocks_without_override():
    d = decide(ACT, "exhausted", DANGER)
    assert d.decision == BLOCK
    assert d.requires_override is True


def test_exhausted_override_allows():
    assert decide(ACT, "exhausted", DANGER, override_ok=True).decision == ALLOW


def test_fail_open_on_unknown_mode():
    assert decide(ACT, "garbage", DANGER).decision == ALLOW


def test_fail_open_on_none_mode():
    assert decide(ACT, None, DANGER).decision == ALLOW
