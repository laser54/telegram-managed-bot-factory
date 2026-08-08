"""Trusted Linux/XDG filesystem layout."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class FactoryPaths:
    config_dir: Path
    data_dir: Path
    state_dir: Path

    @classmethod
    def discover(
        cls, environment: Mapping[str, str] | None = None, home: Path | None = None
    ) -> FactoryPaths:
        env = os.environ if environment is None else environment
        trusted_home = Path.home() if home is None else home
        config_home = Path(env.get("XDG_CONFIG_HOME", trusted_home / ".config"))
        data_home = Path(env.get("XDG_DATA_HOME", trusted_home / ".local" / "share"))
        state_home = Path(env.get("XDG_STATE_HOME", trusted_home / ".local" / "state"))
        return cls(
            config_dir=config_home / "bot-factory",
            data_dir=data_home / "bot-factory",
            state_dir=state_home / "bot-factory",
        )

    @classmethod
    def under(cls, root: Path) -> FactoryPaths:
        return cls(root / "config", root / "data", root / "state")

    @property
    def secret_dir(self) -> Path:
        return self.data_dir / "secrets"

    @property
    def instance_dir(self) -> Path:
        return self.data_dir / "instances"

    @property
    def runtime_dir(self) -> Path:
        return self.state_dir / "runtime"

    @property
    def database_path(self) -> Path:
        return self.state_dir / "factory.sqlite"

    def ensure_non_secret_layout(self) -> None:
        directories = (
            self.config_dir,
            self.data_dir,
            self.state_dir,
            self.instance_dir,
            self.runtime_dir,
        )
        for path in directories:
            path.mkdir(mode=0o700, parents=True, exist_ok=True)
            if path.is_symlink() or not path.is_dir():
                raise ValueError("Factory directory is not a safe directory.")
            path.chmod(0o700)
