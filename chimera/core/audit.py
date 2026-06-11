"""Reflex audit trail — the accountability record for core's autonomy (AD-1).

Core actuates cross-module reflexes on its own authority (lock the vault on tether loss,
ramp/relax obfuscation on anomaly, escalate the dead-man). Those actions otherwise vanish
the moment they scroll past `chimera watch`. AuditLog is the append-only, queryable record
of WHAT core actuated, WHEN, and the OUTCOME — so the operator can answer "why did my vault
lock?" after the fact. Autonomy without accountability is a black box; this closes that gap.

Append-only JSONL, one entry per line, 0600 file in a 0700 dir. A corrupt line is skipped,
never fatal — the trail keeps reading. This is a record of core's OWN actions, not operator
secrets, so it is plaintext (queryable by design); it holds no keys or plaintext payloads.
"""

from __future__ import annotations

import json
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any


class AuditLog:
    """Append-only record of every reflex the core actuates."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    def record(
        self, *, topic: str, commands: Sequence[str], outcome: str
    ) -> dict[str, Any]:
        """Append one reflex actuation (timestamped) and return the stored entry.

        topic   — the event that fired the reflex (e.g. "tether.absent")
        commands— the module.method(s) core issued in response
        outcome — "ok", or a short failure string ("error: module offline")
        """
        entry: dict[str, Any] = {
            "ts": time.time(),
            "topic": topic,
            "commands": list(commands),
            "outcome": outcome,
        }
        self._path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not self._path.exists():
            self._path.touch(mode=0o600)
        self._path.chmod(0o600)
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
        return entry

    def recent(self, n: int = 50) -> list[dict[str, Any]]:
        """The last n actuations in chronological order; [] if nothing recorded.

        A corrupt/half-written line is skipped, never raised — the trail must remain
        readable even after an unclean shutdown."""
        if not self._path.exists():
            return []
        try:
            lines = self._path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        out: list[dict[str, Any]] = []
        for line in lines[-n:]:
            try:
                parsed = json.loads(line)
            except ValueError:
                continue
            if isinstance(parsed, dict):
                out.append(parsed)
        return out
