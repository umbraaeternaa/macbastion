"""Override-phrase store — the §8 autonomy escape for the cognitive gate.

PULSE's exhausted mode blocks danger actions; §8 guarantees the operator can ALWAYS
proceed by typing a pre-set override phrase. The phrase is never stored in the clear —
only a salted PBKDF2 hash (set once, typed in full each time, verified in constant time).
If no phrase is set, verify() is False — override is simply unavailable until configured;
the operator is never silently let through. File 0600 in a 0700 dir.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path

ITERATIONS = 200_000


class OverrideStore:
    """Salted-hash store of the operator's gate-override phrase (OV-1)."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    def is_set(self) -> bool:
        """True if an override phrase has been configured."""
        return self._path.exists()

    def set_phrase(self, phrase: str, *, current: str | None = None) -> bool:
        """Store a salted PBKDF2 hash of the phrase.

        The FIRST set (none configured) needs no current. CHANGING an existing phrase
        requires the correct current phrase (GH-1, §8) — else the change is rejected
        (returns False) and the old phrase stays active. Returns True when stored.
        """
        if self.is_set() and (current is None or not self.verify(current)):
            return False
        salt = os.urandom(16)
        digest = hashlib.pbkdf2_hmac("sha256", phrase.encode("utf-8"), salt, ITERATIONS)
        payload = {"salt": salt.hex(), "hash": digest.hex(), "iterations": ITERATIONS}
        self._path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._path.touch(mode=0o600, exist_ok=True)
        self._path.chmod(0o600)
        self._path.write_text(json.dumps(payload))
        return True

    def verify(self, phrase: str) -> bool:
        """Constant-time check of phrase against the stored hash; False if unset."""
        if not self._path.exists():
            return False
        try:
            data = json.loads(self._path.read_text())
            if not isinstance(data, dict):
                return False
            salt = bytes.fromhex(data["salt"])
            stored = bytes.fromhex(data["hash"])
            iterations = int(data["iterations"])
        except (ValueError, KeyError, TypeError, OSError):
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", phrase.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(candidate, stored)
