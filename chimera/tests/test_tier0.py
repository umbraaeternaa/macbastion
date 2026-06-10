"""PURGE Tier-0 executor (T0-a): evict CHIMERA Keychain items (via shim) + wipe state DBs.
RED: run_tier0 raises NotImplementedError until GREEN."""

from pathlib import Path

from core.shim_client import ShimError
from core.tier0 import run_tier0


class _MockShim:
    def __init__(self, fail: bool = False) -> None:
        self.evict_calls = 0
        self._fail = fail

    async def evict(self) -> dict[str, object]:
        self.evict_calls += 1
        if self._fail:
            raise ShimError(-31004, "shim unreachable")
        return {"ok": True, "noop": False}


async def test_tier0_evicts_keychain_and_wipes_state(tmp_path: Path) -> None:
    state = tmp_path / "state"
    state.mkdir()
    (state / "oracle_baseline.json").write_text("x")
    (state / "pulse_history.db").write_text("y")
    shim = _MockShim()
    report = await run_tier0(shim, state)
    assert shim.evict_calls == 1
    assert report["keychain_evicted"] is True
    assert report["state_files_removed"] == 2
    assert report["errors"] == []
    assert not (state / "oracle_baseline.json").exists()
    assert not (state / "pulse_history.db").exists()


async def test_tier0_wipes_state_even_when_shim_fails(tmp_path: Path) -> None:
    state = tmp_path / "state"
    state.mkdir()
    (state / "vault_meta.json").write_text("z")
    shim = _MockShim(fail=True)
    report = await run_tier0(shim, state)
    assert report["keychain_evicted"] is False
    assert report["state_files_removed"] == 1  # destruction proceeds despite the shim failure
    assert len(report["errors"]) == 1
    assert not (state / "vault_meta.json").exists()


async def test_tier0_empty_state_dir_is_clean(tmp_path: Path) -> None:
    state = tmp_path / "state"
    state.mkdir()
    shim = _MockShim()
    report = await run_tier0(shim, state)
    assert shim.evict_calls == 1
    assert report["state_files_removed"] == 0
    assert report["errors"] == []
