"""PURGE Tier-0 executor (§5.8): destroy CHIMERA's OWN secrets — the Keychain items (via the
privileged shim) and the on-disk state DBs (ORACLE baseline, PULSE history, VAULT metadata
under state_dir).

Keys-first + best-effort: evict the Keychain first (the crown jewels), then wipe state; a
failure in one step never aborts the others — a destruction op does as much as it can and
reports every error. State files are unlinked, NOT secure-overwritten: on wear-levelled SSD an
overwrite cannot be guaranteed (§8), so Tier-0 removes the files and the real secrecy guarantee
rides on the evicted Keychain / crypto-shredded keys (Tier-1).

RED: run_tier0 raises NotImplementedError (MANIFESTO §4 — no faked destruction).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Protocol

from core.shim_client import ShimError


class SupportsEvict(Protocol):
    """The slice of ShimClient Tier-0 needs: evict the CHIMERA Keychain items."""

    async def evict(self) -> dict[str, object]: ...


def _wipe_state_dir(state_dir: Path) -> tuple[int, list[str]]:
    """Unlink every file under state_dir (synchronous; run off-loop). Returns (removed, errors)."""
    removed = 0
    errors: list[str] = []
    if state_dir.exists():
        for entry in sorted(state_dir.rglob("*")):
            if entry.is_file():
                try:
                    entry.unlink()
                    removed += 1
                except OSError as exc:
                    errors.append(f"state file {entry.name}: {exc}")
    return removed, errors


async def run_tier0(shim: SupportsEvict, state_dir: Path) -> dict[str, object]:
    """Evict CHIMERA Keychain items, then wipe the state DBs under state_dir. Returns a report
    {keychain_evicted, state_files_removed, errors}."""
    errors: list[str] = []

    # Keys first: evict the Keychain (the crown jewels) before anything else.
    keychain_evicted = False
    try:
        await shim.evict()
        keychain_evicted = True
    except ShimError as exc:
        errors.append(f"keychain evict: {exc}")

    # Then wipe the on-disk state DBs — best-effort, regardless of the eviction outcome.
    state_files_removed, wipe_errors = await asyncio.to_thread(_wipe_state_dir, state_dir)
    errors.extend(wipe_errors)

    return {
        "keychain_evicted": keychain_evicted,
        "state_files_removed": state_files_removed,
        "errors": errors,
    }
