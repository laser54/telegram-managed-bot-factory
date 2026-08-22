"""Isolated Linux child runtime materialization and supervision."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Literal, Protocol
from uuid import UUID

from pydantic import Field

from telegram_bot_factory.models import (
    FactoryRequest,
    ProfileConfig,
    ProfileName,
    Slug,
    StrictModel,
)
from telegram_bot_factory.paths import FactoryPaths
from telegram_bot_factory.secrets import LocalFileSecretStore


class RuntimeProvisionError(RuntimeError):
    """Safe local runtime failure."""


class RuntimeLauncher(Protocol):
    def materialize_and_start(self, request: FactoryRequest) -> object: ...


class InstanceManifest(StrictModel):
    schema_version: Literal[1] = 1
    slug: Slug
    request_id: UUID
    username: str
    owner_telegram_id: int = Field(gt=0)
    profile: ProfileName
    profile_config: ProfileConfig
    created_at: datetime


class InstanceLauncher:
    def __init__(self, paths: FactoryPaths, secrets: LocalFileSecretStore) -> None:
        self._paths = paths
        self._secrets = secrets
        self._processes: dict[str, subprocess.Popen[bytes]] = {}

    def materialize(self, request: FactoryRequest) -> InstanceManifest:
        self._paths.ensure_non_secret_layout()
        instance_dir = self._safe_child(self._paths.instance_dir, request.slug)
        runtime_dir = self._safe_child(self._paths.runtime_dir, request.slug)
        if instance_dir.exists():
            raise RuntimeProvisionError("Instance slug already exists.")
        try:
            instance_dir.mkdir(mode=0o700)
            runtime_dir.mkdir(mode=0o700, exist_ok=False)
            instance_dir.chmod(0o700)
            runtime_dir.chmod(0o700)
            manifest = InstanceManifest(
                slug=request.slug,
                request_id=request.request_id,
                username=request.username,
                owner_telegram_id=request.owner_telegram_id,
                profile=request.profile,
                profile_config=request.profile_config,
                created_at=request.created_at,
            )
            self._write_manifest(instance_dir / "manifest.json", manifest)
        except (OSError, ValueError) as error:
            raise RuntimeProvisionError("Instance could not be materialized safely.") from error
        return manifest

    def start(self, manifest: InstanceManifest) -> None:
        if os.name != "posix":
            raise RuntimeProvisionError("Child runtime is supported on Linux only.")
        slug = str(manifest.slug)
        existing = self._processes.get(slug)
        if existing is not None and existing.poll() is None:
            raise RuntimeProvisionError("Instance is already running.")
        runtime_dir = self._safe_child(self._paths.runtime_dir, manifest.slug)
        manifest_path = self._safe_child(self._paths.instance_dir, manifest.slug) / "manifest.json"
        credential = self._secrets.read_child(manifest.slug)
        read_fd, write_fd = os.pipe()
        try:
            os.set_inheritable(read_fd, True)
            command = [
                sys.executable,
                "-m",
                "telegram_bot_factory.child_process",
                "--token-fd",
                str(read_fd),
                "--manifest",
                str(manifest_path),
                "--runtime-dir",
                str(runtime_dir),
            ]
            process = subprocess.Popen(  # noqa: S603 - fixed interpreter and module
                command,
                cwd=runtime_dir,
                env=self._child_environment(),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                close_fds=True,
                pass_fds=(read_fd,),
            )
            os.close(read_fd)
            read_fd = -1
            payload = credential.encode("utf-8")
            sent = 0
            while sent < len(payload):
                sent += os.write(write_fd, payload[sent:])
            self._processes[slug] = process
        except OSError as error:
            raise RuntimeProvisionError("Child process could not be started safely.") from error
        finally:
            credential = ""
            if read_fd >= 0:
                os.close(read_fd)
            os.close(write_fd)

    def materialize_and_start(self, request: FactoryRequest) -> InstanceManifest:
        manifest = self.materialize(request)
        self.start(manifest)
        return manifest

    def rebind(self, slug: Slug, profile: ProfileName, profile_config: ProfileConfig) -> None:
        """Replace only the allowlisted profile portion of an existing manifest."""
        manifest_path = self._safe_child(self._paths.instance_dir, slug) / "manifest.json"
        current = self.load_manifest(manifest_path)
        updated = current.model_copy(update={"profile": profile, "profile_config": profile_config})
        self._write_manifest(manifest_path, updated)

    def stop(self, slug: Slug, wait_seconds: float = 10) -> None:
        process = self._processes.get(str(slug))
        if process is None or process.poll() is not None:
            raise RuntimeProvisionError("Instance is not running.")
        process.terminate()
        try:
            process.wait(timeout=wait_seconds)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        finally:
            if process.stderr is not None:
                process.stderr.close()
            self._processes.pop(str(slug), None)

    def is_running(self, slug: Slug) -> bool:
        process = self._processes.get(str(slug))
        return process is not None and process.poll() is None

    def shutdown(self) -> None:
        for raw_slug in list(self._processes):
            try:
                self.stop(raw_slug)
            except RuntimeProvisionError:
                continue

    @staticmethod
    def _child_environment() -> dict[str, str]:
        environment = {"PYTHONUNBUFFERED": "1"}
        for key in ("LANG", "LC_ALL", "PATH"):
            if value := os.environ.get(key):
                environment[key] = value
        return environment

    @staticmethod
    def _safe_child(parent: Path, slug: Slug) -> Path:
        parent_resolved = parent.resolve()
        child = parent / str(slug)
        if child.is_symlink():
            raise RuntimeProvisionError("Instance path is unsafe.")
        try:
            child.resolve(strict=False).relative_to(parent_resolved)
        except ValueError as error:
            raise RuntimeProvisionError("Instance path escapes its trusted parent.") from error
        return child

    @staticmethod
    def _write_manifest(path: Path, manifest: InstanceManifest) -> None:
        temporary = path.with_name(".manifest.pending")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        descriptor: int | None = None
        try:
            descriptor = os.open(temporary, flags, 0o600)
            payload = manifest.model_dump_json(indent=2).encode("utf-8") + b"\n"
            written = 0
            while written < len(payload):
                written += os.write(descriptor, payload[written:])
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = None
            os.replace(temporary, path)
            path.chmod(0o600)
        finally:
            if descriptor is not None:
                os.close(descriptor)
            temporary.unlink(missing_ok=True)

    @staticmethod
    def load_manifest(path: Path) -> InstanceManifest:
        try:
            if path.is_symlink() or path.stat().st_size > 64 * 1024:
                raise RuntimeProvisionError("Instance manifest is unsafe.")
            return InstanceManifest.model_validate_json(path.read_bytes(), strict=True)
        except (OSError, ValueError) as error:
            raise RuntimeProvisionError("Instance manifest is invalid.") from error
