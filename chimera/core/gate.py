"""Cognitive gate decision — core enforcement of PULSE's advisory mode (§4 friction,
§8 autonomy invariant). GE-1…GE-5, slice 1: the PURE decision heart.

PULSE only emits its mode; core decides what friction (if any) a danger action gets.
This module is the decision — no I/O, no wire, no mode-tracking yet (that wiring is a
follow-up slice). fail-OPEN (§8): an unknown/missing mode never blocks — a broken
cognitive sensor must not lock the operator out (the opposite of VAULT's fail-closed).
The override phrase is always a speed bump, never a cage: at `exhausted` a correct
override still allows the action.

RED stub: GateDecision + the §4 friction vocabulary are fixed; decide() raises
NotImplementedError so the failing tests are real (MANIFESTO §4).
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
    """Friction for one action given PULSE's current mode (§4 + §8). RED stub."""
    raise NotImplementedError
