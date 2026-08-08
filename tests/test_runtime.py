import os
from pathlib import Path

import pytest

from telegram_bot_factory.child_process import read_token_fd
from telegram_bot_factory.models import CreateRequest, FactoryRequest, OwnerEchoConfig
from telegram_bot_factory.paths import FactoryPaths
from telegram_bot_factory.runtime import InstanceLauncher, RuntimeProvisionError
from telegram_bot_factory.secrets import LocalFileSecretStore

SENTINEL = "REDACTED_TOKEN_SHAPE"


def make_request() -> FactoryRequest:
    return FactoryRequest.from_create(
        CreateRequest(
            display_name="Owner Echo",
            username="owner_echo_bot",
            slug="owner_echo",
            profile_config=OwnerEchoConfig(),
            owner_telegram_id=42,
        )
    )


def test_manifest_is_non_secret_and_cannot_be_overwritten(tmp_path: Path) -> None:
    paths = FactoryPaths.under(tmp_path)
    launcher = InstanceLauncher(paths, LocalFileSecretStore(paths))
    request = make_request()

    manifest = launcher.materialize(request)
    manifest_bytes = (paths.instance_dir / "owner_echo" / "manifest.json").read_bytes()

    assert manifest.slug == "owner_echo"
    assert SENTINEL.encode() not in manifest_bytes
    assert InstanceLauncher.load_manifest(
        paths.instance_dir / "owner_echo" / "manifest.json"
    ) == manifest
    with pytest.raises(RuntimeProvisionError, match="already exists"):
        launcher.materialize(request)


def test_child_environment_does_not_inherit_secret_bearing_variables(monkeypatch: object) -> None:
    os.environ["HERMES_API_KEY"] = SENTINEL
    os.environ["BW_ACCESS_TOKEN"] = SENTINEL
    os.environ["BOT_FACTORY_MANAGER_TOKEN_FILE"] = SENTINEL
    try:
        environment = InstanceLauncher._child_environment()
    finally:
        os.environ.pop("HERMES_API_KEY")
        os.environ.pop("BW_ACCESS_TOKEN")
        os.environ.pop("BOT_FACTORY_MANAGER_TOKEN_FILE")
    assert SENTINEL not in environment.values()
    assert set(environment) <= {"PYTHONUNBUFFERED", "LANG", "LC_ALL", "PATH"}


def test_token_pipe_reader_closes_descriptor() -> None:
    read_fd, write_fd = os.pipe()
    os.write(write_fd, SENTINEL.encode())
    os.close(write_fd)

    assert read_token_fd(read_fd) == SENTINEL
