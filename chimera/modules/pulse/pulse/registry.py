"""PULSE danger registry — operator-editable list of danger-action signatures
(§5.5 §4/§6/§7, DR-1…DR-6).

Plain JSON at registry.json (operator-editable, §7) — NOT encrypted: it is the
operator's config (which actions to gate), not raw behavioural data, unlike the baseline
store. On first creation it seeds the §4 defaults; add/remove are idempotent. File 0600
in a 0700 dir (privacy posture; the owner can still edit it by hand).
"""

from __future__ import annotations

import json
from pathlib import Path

# Builtin list[str] aliased at module scope — the `list` METHOD below would otherwise
# shadow the builtin inside the class, breaking `-> list[str]` annotations.
Signatures = list[str]

# §4 default danger actions — operator-editable signature strings.
DEFAULT_DANGERS: Signatures = [
    "rm:$HOME",
    "purge.trigger",
    "vault.unlock:out-of-window",
    "browser.post:financial",
    "git:push --force",
    "send:high-stakes",
]


class DangerRegistry:
    """Operator's danger-action list, persisted as plain JSON (DR-1)."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        if not self._path.exists():
            self._write(list(DEFAULT_DANGERS))  # DR-2: seed §4 defaults on first use

    def _write(self, items: Signatures) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._path.touch(mode=0o600, exist_ok=True)
        self._path.chmod(0o600)
        self._path.write_text(json.dumps(items, indent=2))

    def _read(self) -> Signatures:
        if not self._path.exists():
            return list(DEFAULT_DANGERS)
        data = json.loads(self._path.read_text())
        return [str(s) for s in data] if isinstance(data, list) else list(DEFAULT_DANGERS)

    def list(self) -> Signatures:
        """Current danger-action signatures."""
        return self._read()

    def add(self, signature: str) -> Signatures:
        """Add a signature (idempotent — no duplicates); persist; return the list."""
        items = self._read()
        if signature not in items:
            items.append(signature)
            self._write(items)
        return items

    def remove(self, signature: str) -> Signatures:
        """Remove a signature (idempotent — no error if absent); persist; return list."""
        items = self._read()
        if signature in items:
            items.remove(signature)
            self._write(items)
        return items
