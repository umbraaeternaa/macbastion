"""PULSE danger registry — operator-editable list of danger-action signatures
(§5.5 §4/§6/§7, DR-1…DR-6).

Plain JSON at registry.json (operator-editable, §7) — NOT encrypted: it is the
operator's config (which actions to gate), not raw behavioural data, unlike the baseline
store. On first creation it seeds the §4 defaults; add/remove are idempotent.

RED stub: the public surface is fixed; behaviour raises NotImplementedError so the
failing tests are real (an honest empty stub — MANIFESTO §4). __init__ stores the path
only; no file is created or seeded until GREEN.
"""

from __future__ import annotations

from pathlib import Path

# §4 default danger actions — operator-editable signature strings.
DEFAULT_DANGERS = [
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

    def list(self) -> list[str]:
        """Current danger-action signatures (seeds §4 defaults on first use)."""
        raise NotImplementedError

    def add(self, signature: str) -> list[str]:
        """Add a signature (idempotent — no duplicates); persist; return the list."""
        raise NotImplementedError

    def remove(self, signature: str) -> list[str]:
        """Remove a signature (idempotent — no error if absent); persist; return list."""
        raise NotImplementedError
