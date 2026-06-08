"""Override-phrase store — the §8 autonomy escape for the cognitive gate.

PULSE's exhausted mode blocks danger actions; §8 guarantees the operator can ALWAYS
proceed by typing a pre-set override phrase. The phrase is never stored in the clear —
only a salted PBKDF2 hash (set once, typed in full each time, verified in constant time).
If no phrase is set, verify() is False — override is simply unavailable until configured;
the operator is never silently let through.

RED stub: the public surface is fixed; methods raise NotImplementedError (MANIFESTO §4).
"""

from __future__ import annotations

from pathlib import Path

ITERATIONS = 200_000


class OverrideStore:
    """Salted-hash store of the operator's gate-override phrase (OV-1)."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    def is_set(self) -> bool:
        """True if an override phrase has been configured."""
        raise NotImplementedError

    def set_phrase(self, phrase: str) -> None:
        """Store a salted PBKDF2 hash of the phrase (replaces any existing)."""
        raise NotImplementedError

    def verify(self, phrase: str) -> bool:
        """Constant-time check of phrase against the stored hash; False if unset."""
        raise NotImplementedError
