"""Local credential storage with owner-only filesystem permissions."""

from __future__ import annotations

import os
import secrets
import stat
from pathlib import Path

from telegram_bot_factory.models import Slug
from telegram_bot_factory.paths import FactoryPaths


class SecretStoreError(RuntimeError):
    """Safe secret-store failure without credential or path rendering."""


class LocalFileSecretStore:
    def __init__(self, paths: FactoryPaths) -> None:
        self._root = paths.secret_dir
        self._children = self._root / "children"

    def initialize(self) -> None:
        self._ensure_private_directory(self._root)
        self._ensure_private_directory(self._children)

    def write_manager(self, value: str, *, overwrite: bool = False) -> None:
        self._write(self._root / "manager-token", value, overwrite=overwrite)

    def read_manager(self) -> str:
        return self._read(self._root / "manager-token")

    def write_child(self, slug: Slug, value: str) -> None:
        self._write(self._children / str(slug), value, overwrite=False)

    def read_child(self, slug: Slug) -> str:
        return self._read(self._children / str(slug))

    def manager_configured(self) -> bool:
        return self._safe_regular_file(self._root / "manager-token")

    def child_configured(self, slug: Slug) -> bool:
        return self._safe_regular_file(self._children / str(slug))

    @staticmethod
    def _ensure_private_directory(path: Path) -> None:
        try:
            path.mkdir(mode=0o700, parents=True, exist_ok=True)
            if path.is_symlink() or not path.is_dir():
                raise SecretStoreError("Secret directory is unsafe.")
            path.chmod(0o700)
            LocalFileSecretStore._verify_owner(path)
        except OSError as error:
            raise SecretStoreError("Secret directory could not be secured.") from error

    @staticmethod
    def _verify_owner(path: Path) -> None:
        # Windows type stubs omit getuid even though this branch is Linux-only.
        if os.name == "posix" and path.stat().st_uid != getattr(os, "getuid")():  # noqa: B009
            raise SecretStoreError("Secret path is not owned by the current user.")

    @staticmethod
    def _validate_secret(value: str) -> bytes:
        if not value or "\n" in value or "\r" in value or len(value) > 4096:
            raise SecretStoreError("Credential has an invalid shape.")
        return value.encode("utf-8")

    def _write(self, destination: Path, value: str, *, overwrite: bool) -> None:
        self.initialize()
        data = self._validate_secret(value)
        if destination.exists() and not overwrite:
            raise SecretStoreError("Credential is already configured.")
        temporary = destination.parent / f".pending-{secrets.token_hex(12)}"
        nofollow = getattr(os, "O_NOFOLLOW", 0)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | nofollow
        descriptor: int | None = None
        try:
            descriptor = os.open(temporary, flags, 0o600)
            written = 0
            while written < len(data):
                written += os.write(descriptor, data[written:])
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = None
            temporary.chmod(0o600)
            if destination.is_symlink():
                raise SecretStoreError("Credential destination is unsafe.")
            if destination.exists() and not overwrite:
                raise SecretStoreError("Credential is already configured.")
            if overwrite:
                os.replace(temporary, destination)
            else:
                os.link(temporary, destination, follow_symlinks=False)
                temporary.unlink()
            destination.chmod(0o600)
            self._verify_private_file(destination)
        except OSError as error:
            raise SecretStoreError("Credential could not be stored securely.") from error
        finally:
            if descriptor is not None:
                os.close(descriptor)
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

    def _read(self, path: Path) -> str:
        self._verify_private_file(path)
        nofollow = getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(path, os.O_RDONLY | nofollow)
            try:
                data = os.read(descriptor, 4097)
            finally:
                os.close(descriptor)
        except OSError as error:
            raise SecretStoreError("Credential could not be read securely.") from error
        if len(data) > 4096:
            raise SecretStoreError("Credential file is unexpectedly large.")
        return data.decode("utf-8")

    @staticmethod
    def _safe_regular_file(path: Path) -> bool:
        try:
            LocalFileSecretStore._verify_private_file(path)
        except SecretStoreError:
            return False
        return True

    @staticmethod
    def _verify_private_file(path: Path) -> None:
        try:
            info = path.lstat()
        except OSError as error:
            raise SecretStoreError("Credential is not configured.") from error
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            raise SecretStoreError("Credential path is unsafe.")
        if os.name == "posix" and stat.S_IMODE(info.st_mode) != 0o600:
            raise SecretStoreError("Credential permissions are unsafe.")
        LocalFileSecretStore._verify_owner(path)
