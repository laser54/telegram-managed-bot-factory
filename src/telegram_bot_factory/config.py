"""Non-secret local Factory configuration."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field

from telegram_bot_factory.models import StrictModel


class FactoryConfigError(RuntimeError):
    """Safe non-secret configuration failure."""


class FactoryConfig(StrictModel):
    schema_version: int = Field(default=1, ge=1, le=1)
    manager_username: str = Field(min_length=5, max_length=32, pattern=r"^[A-Za-z0-9_]+$")
    manager_user_id: int = Field(gt=0)
    can_manage_bots: bool
    owner_allowlist: list[int] = Field(min_length=1, max_length=10)

    def owner_allowed(self, owner_telegram_id: int) -> bool:
        return owner_telegram_id in self.owner_allowlist


def write_factory_config(path: Path, config: FactoryConfig) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    if path.is_symlink():
        raise FactoryConfigError("Factory configuration path is unsafe.")
    temporary = path.with_name(".config.pending")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor: int | None = None
    try:
        descriptor = os.open(temporary, flags, 0o600)
        payload = config.model_dump_json(indent=2).encode("utf-8") + b"\n"
        sent = 0
        while sent < len(payload):
            sent += os.write(descriptor, payload[sent:])
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        os.replace(temporary, path)
        path.chmod(0o600)
    except OSError as error:
        raise FactoryConfigError("Factory configuration could not be stored.") from error
    finally:
        if descriptor is not None:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def read_factory_config(path: Path) -> FactoryConfig:
    try:
        if path.is_symlink() or path.stat().st_size > 64 * 1024:
            raise FactoryConfigError("Factory configuration is unsafe.")
        return FactoryConfig.model_validate_json(path.read_bytes(), strict=True)
    except (OSError, ValueError) as error:
        raise FactoryConfigError("Factory configuration is unavailable or invalid.") from error

