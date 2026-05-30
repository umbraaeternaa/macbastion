"""Core configuration — paths, defaults, env (§6.3 + §7 + §8)."""

import os
import tomllib
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CoreConfig(BaseSettings):
    """CHIMERA core configuration.

    Hierarchy: env vars (CHIMERA_*) > TOML file > code defaults.
    Immutable after load (decision 5A).
    """

    model_config = SettingsConfigDict(
        env_prefix="CHIMERA_",
        frozen=True,
        extra="forbid",
    )

    # Paths (§6.3)
    socket_dir: Path = Path("~/.config/chimera/run").expanduser()
    state_dir: Path = Path("~/.config/chimera/state").expanduser()
    log_dir: Path = Path("~/.config/chimera/logs").expanduser()
    config_file: Path = Path("~/.config/chimera/config.toml").expanduser()

    # Heartbeat (§7.4)
    heartbeat_interval_s: int = 10
    heartbeat_jitter_tolerance: int = 1
    heartbeat_dead_threshold: int = 3

    # Restart policy (§7.5)
    restart_max_per_hour: int = 5
    shutdown_timeout_s: int = 5

    # Security (§8)
    socket_mode: int = 0o600
    socket_dir_mode: int = 0o700
    log_retention_days: int = 30
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    @field_validator("socket_dir", "state_dir", "log_dir", "config_file", mode="before")
    @classmethod
    def _normalize_paths(cls, v: object) -> Path:
        if isinstance(v, str):
            path = Path(v)
        elif isinstance(v, Path):
            path = v
        else:
            raise TypeError(f"path must be str or Path, got {type(v).__name__}")
        path = path.expanduser()
        if not path.is_absolute():
            raise ValueError(f"path must be absolute (after ~ expansion), got: {path}")
        return path

    @model_validator(mode="after")
    def _reject_unknown_chimera_env_vars(self) -> Self:
        # pydantic-settings silently filters env vars to known fields, so
        # extra="forbid" never sees unknown CHIMERA_* vars. Surface them
        # explicitly: an unknown CHIMERA_* in the environment is a config bug.
        for key in os.environ:
            if key.startswith("CHIMERA_"):
                field_name = key.removeprefix("CHIMERA_").lower()
                if field_name not in type(self).model_fields:
                    raise ValueError(f"unknown environment variable: {key}")
        return self

    @classmethod
    def from_toml(cls, path: Path) -> Self:
        """Load config from a TOML file. A missing file falls back to defaults."""
        if not path.exists():
            return cls()
        with path.open("rb") as f:
            data = tomllib.load(f)
        return cls(**data)

    @classmethod
    def from_env_and_toml(cls, toml_path: Path | None = None) -> Self:
        """Compose the full env > toml > defaults hierarchy."""
        toml_data: dict[str, Any] = {}
        if toml_path is not None and toml_path.exists():
            with toml_path.open("rb") as f:
                toml_data = tomllib.load(f)

        env_data: dict[str, str] = {}
        for key, value in os.environ.items():
            if key.startswith("CHIMERA_"):
                env_data[key.removeprefix("CHIMERA_").lower()] = value

        merged: dict[str, Any] = {**toml_data, **env_data}
        return cls(**merged)
