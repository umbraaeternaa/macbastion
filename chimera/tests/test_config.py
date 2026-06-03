"""Tests for config module (§6.3 paths + §7 lifecycle + §8 security)."""

import os
import tomllib
from pathlib import Path

import pytest
from core.config import CoreConfig
from pydantic import ValidationError


@pytest.fixture(autouse=True)
def _clear_chimera_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear any CHIMERA_* env vars so default-tests are not polluted by the shell."""
    for key in list(os.environ):
        if key.startswith("CHIMERA_"):
            monkeypatch.delenv(key, raising=False)


# ---------------------------------------------------------------------------
# Code defaults — the lowest-priority layer of the hierarchy
# ---------------------------------------------------------------------------


class TestCoreConfigDefaults:
    """Defaults match §6.3 paths, §7 lifecycle timing, and §8 security values."""

    def test_default_socket_dir_is_xdg_config(self) -> None:
        assert CoreConfig().socket_dir == Path.home() / ".config/chimera/run"

    def test_default_state_dir_is_xdg_config(self) -> None:
        assert CoreConfig().state_dir == Path.home() / ".config/chimera/state"

    def test_default_log_dir_is_xdg_config(self) -> None:
        assert CoreConfig().log_dir == Path.home() / ".config/chimera/logs"

    def test_default_heartbeat_interval_is_10(self) -> None:
        assert CoreConfig().heartbeat_interval_s == 10

    def test_default_heartbeat_thresholds(self) -> None:
        config = CoreConfig()
        assert config.heartbeat_jitter_tolerance == 1
        assert config.heartbeat_dead_threshold == 3

    def test_default_restart_max_per_hour_is_5(self) -> None:
        assert CoreConfig().restart_max_per_hour == 5

    def test_default_shutdown_timeout_is_5s(self) -> None:
        assert CoreConfig().shutdown_timeout_s == 5

    def test_default_request_timeout_is_5s(self) -> None:
        assert CoreConfig().request_timeout_s == 5.0

    def test_default_socket_mode_is_0600(self) -> None:
        config = CoreConfig()
        assert config.socket_mode == 0o600
        assert config.socket_mode == 384  # decimal sanity

    def test_default_socket_dir_mode_is_0700(self) -> None:
        config = CoreConfig()
        assert config.socket_dir_mode == 0o700
        assert config.socket_dir_mode == 448  # decimal sanity

    def test_default_log_retention_30_days(self) -> None:
        assert CoreConfig().log_retention_days == 30

    def test_default_log_level_is_info(self) -> None:
        assert CoreConfig().log_level == "INFO"


# ---------------------------------------------------------------------------
# from_toml() — TOML file loading (middle layer)
# ---------------------------------------------------------------------------


class TestCoreConfigFromToml:
    """from_toml() loads a TOML file; missing fields fall back to defaults."""

    def test_loads_existing_toml_overrides_defaults(self, tmp_path: Path) -> None:
        toml_path = tmp_path / "config.toml"
        toml_path.write_text("heartbeat_interval_s = 20\n")
        assert CoreConfig.from_toml(toml_path).heartbeat_interval_s == 20

    def test_partial_toml_uses_defaults_for_missing(self, tmp_path: Path) -> None:
        toml_path = tmp_path / "config.toml"
        toml_path.write_text('log_level = "DEBUG"\n')
        config = CoreConfig.from_toml(toml_path)
        assert config.log_level == "DEBUG"
        assert config.heartbeat_interval_s == 10  # default

    def test_missing_toml_file_returns_defaults(self, tmp_path: Path) -> None:
        nonexistent = tmp_path / "does_not_exist.toml"
        config = CoreConfig.from_toml(nonexistent)
        assert config.log_level == "INFO"
        assert config.heartbeat_interval_s == 10

    def test_malformed_toml_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.toml"
        bad.write_text("not = valid = toml")
        with pytest.raises(tomllib.TOMLDecodeError):
            CoreConfig.from_toml(bad)

    def test_unknown_field_in_toml_rejected(self, tmp_path: Path) -> None:
        toml_path = tmp_path / "config.toml"
        toml_path.write_text('foo = "bar"\n')
        with pytest.raises(ValidationError):
            CoreConfig.from_toml(toml_path)


# ---------------------------------------------------------------------------
# Env vars (CHIMERA_*) — highest priority
# ---------------------------------------------------------------------------


class TestCoreConfigFromEnv:
    """Env vars override TOML and defaults."""

    def test_env_overrides_log_level(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CHIMERA_LOG_LEVEL", "DEBUG")
        assert CoreConfig().log_level == "DEBUG"

    def test_env_overrides_heartbeat_interval(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CHIMERA_HEARTBEAT_INTERVAL_S", "20")
        assert CoreConfig().heartbeat_interval_s == 20

    def test_env_overrides_request_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CHIMERA_REQUEST_TIMEOUT_S", "2.5")
        assert CoreConfig().request_timeout_s == 2.5

    def test_request_timeout_must_be_positive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CHIMERA_REQUEST_TIMEOUT_S", "0")
        with pytest.raises(ValidationError):
            CoreConfig()

    def test_env_invalid_log_level_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CHIMERA_LOG_LEVEL", "INVALID")
        with pytest.raises(ValidationError):
            CoreConfig()

    def test_env_wrong_type_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CHIMERA_HEARTBEAT_INTERVAL_S", "not_a_number")
        with pytest.raises(ValidationError):
            CoreConfig()

    def test_unknown_env_var_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CHIMERA_UNKNOWN", "value")
        with pytest.raises(ValidationError):
            CoreConfig()


# ---------------------------------------------------------------------------
# Priority hierarchy — env > toml > defaults
# ---------------------------------------------------------------------------


class TestPriorityHierarchy:
    """from_env_and_toml() composes the full env > toml > defaults hierarchy."""

    def test_env_overrides_toml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        toml_path = tmp_path / "config.toml"
        toml_path.write_text('log_level = "WARNING"\n')
        monkeypatch.setenv("CHIMERA_LOG_LEVEL", "DEBUG")
        assert CoreConfig.from_env_and_toml(toml_path).log_level == "DEBUG"

    def test_toml_overrides_defaults_when_env_absent(self, tmp_path: Path) -> None:
        toml_path = tmp_path / "config.toml"
        toml_path.write_text('log_level = "ERROR"\n')
        assert CoreConfig.from_env_and_toml(toml_path).log_level == "ERROR"

    def test_defaults_when_no_env_no_toml(self) -> None:
        assert CoreConfig.from_env_and_toml(None).log_level == "INFO"


# ---------------------------------------------------------------------------
# Path resolution — Path objects, absolute, ~ expanded
# ---------------------------------------------------------------------------


class TestPathResolution:
    """Path fields are Path objects, absolute, and expand ~."""

    def test_socket_dir_is_path_object(self) -> None:
        assert isinstance(CoreConfig().socket_dir, Path)

    def test_socket_dir_is_absolute(self) -> None:
        assert CoreConfig().socket_dir.is_absolute()

    def test_tilde_in_toml_is_expanded(self, tmp_path: Path) -> None:
        toml_path = tmp_path / "config.toml"
        toml_path.write_text('socket_dir = "~/custom/run"\n')
        config = CoreConfig.from_toml(toml_path)
        assert config.socket_dir == Path.home() / "custom/run"

    def test_relative_path_in_toml_rejected(self, tmp_path: Path) -> None:
        # Decision: relative paths are rejected — explicit-config beats guessing.
        toml_path = tmp_path / "config.toml"
        toml_path.write_text('socket_dir = "./relative"\n')
        with pytest.raises(ValidationError):
            CoreConfig.from_toml(toml_path)


# ---------------------------------------------------------------------------
# Immutability — config is frozen after load (decision 5A)
# ---------------------------------------------------------------------------


class TestImmutability:
    """A loaded CoreConfig cannot be mutated."""

    def test_cannot_assign_to_field(self) -> None:
        config = CoreConfig()
        with pytest.raises(ValidationError):
            config.heartbeat_interval_s = 20

    def test_cannot_add_new_field(self) -> None:
        config = CoreConfig()
        with pytest.raises((ValidationError, AttributeError)):
            config.new_field = "x"


# ---------------------------------------------------------------------------
# Security defaults — alignment with §8 invariants
# ---------------------------------------------------------------------------


class TestSecurityDefaults:
    """Default values protect the operator out of the box (§8)."""

    def test_socket_mode_is_user_only_rw(self) -> None:
        config = CoreConfig()
        assert config.socket_mode == 0o600
        assert oct(config.socket_mode) == "0o600"

    def test_socket_dir_mode_is_user_only_rwx(self) -> None:
        assert CoreConfig().socket_dir_mode == 0o700

    def test_log_retention_is_reasonable(self) -> None:
        config = CoreConfig()
        assert 0 < config.log_retention_days <= 90
