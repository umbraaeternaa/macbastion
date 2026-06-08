"""Cognitive gate decision — core enforcement of PULSE's advisory mode (§4 friction,
§8 autonomy invariant). GE-1…GE-5, slice 1: the PURE decision heart.

PULSE only emits its mode; core decides what friction (if any) a danger action gets.
This module is the decision — no I/O, no wire, no mode-tracking yet (that wiring is a
follow-up slice). fail-OPEN (§8): an unknown/missing mode never blocks — a broken
cognitive sensor must not lock the operator out (the opposite of VAULT's fail-closed).
The override phrase is always a speed bump, never a cage: at `exhausted` a correct
override still allows the action.

GREEN: decide() implements the §4 friction levels + §8 fail-open + the override escape;
pure (no I/O), so it is unit-tested directly.
"""

from __future__ import annotations

from dataclasses import dataclass

# §4 friction levels — the decision vocabulary.
ALLOW = "allow"
CONFIRM = "confirm"  # caution: +1 confirmation dialog
DELAY = "delay"  # tired: +N-second cool-off
BLOCK = "block"  # exhausted: refused unless the override phrase is given

TIRED_DELAY_S = 5.0


@dataclass(frozen=True)
class GateDecision:
    """What friction a danger action gets (GE-1)."""

    decision: str
    delay_seconds: float = 0.0
    requires_override: bool = False
    reason: str = ""


def decide(
    action_signature: str,
    mode: str | None,
    danger: set[str],
    *,
    override_ok: bool = False,
) -> GateDecision:
    """Friction for one action given PULSE's current mode (§4 + §8).

    GE-2 levels, GE-3 fail-open, GE-4 override. Pure — the caller supplies the verified
    override_ok flag (the salted-hash check of the phrase is a separate concern).
    """
    if action_signature not in danger:
        return GateDecision(ALLOW, reason="not a registered danger action")
    if mode == "caution":
        return GateDecision(CONFIRM, reason="caution: confirm before proceeding")
    if mode == "tired":
        return GateDecision(
            DELAY, delay_seconds=TIRED_DELAY_S, reason="tired: cool-off delay"
        )
    if mode == "exhausted":
        if override_ok:
            return GateDecision(ALLOW, reason="exhausted: override accepted")
        return GateDecision(
            BLOCK, requires_override=True, reason="exhausted: override required"
        )
    if mode == "normal":
        return GateDecision(ALLOW, reason="normal: no friction")
    return GateDecision(ALLOW, reason="fail-open: mode unknown")  # §8: never block
