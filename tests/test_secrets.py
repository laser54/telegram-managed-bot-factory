import os
import stat
from pathlib import Path

import pytest

from telegram_bot_factory.models import Slug
from telegram_bot_factory.paths import FactoryPaths
from telegram_bot_factory.secrets import LocalFileSecretStore, SecretStoreError

SENTINEL = "REDACTED_TOKEN_SHAPE"


def test_manager_and_child_round_trip(tmp_path: Path) -> None:
    paths = FactoryPaths.under(tmp_path)
    store = LocalFileSecretStore(paths)
    store.write_manager(SENTINEL)
    store.write_child(Slug("owner_echo"), SENTINEL + "_child")

    assert store.read_manager() == SENTINEL
    assert store.read_child(Slug("owner_echo")) == SENTINEL + "_child"
    assert store.manager_configured()
    assert store.child_configured(Slug("owner_echo"))

    if os.name == "posix":
        assert stat.S_IMODE(paths.secret_dir.stat().st_mode) == 0o700
        assert stat.S_IMODE((paths.secret_dir / "manager-token").stat().st_mode) == 0o600


def test_child_secret_cannot_be_overwritten(tmp_path: Path) -> None:
    store = LocalFileSecretStore(FactoryPaths.under(tmp_path))
    store.write_child(Slug("owner_echo"), SENTINEL)
    with pytest.raises(SecretStoreError, match="already configured"):
        store.write_child(Slug("owner_echo"), SENTINEL + "_other")


def test_secret_error_does_not_render_value(tmp_path: Path) -> None:
    store = LocalFileSecretStore(FactoryPaths.under(tmp_path))
    with pytest.raises(SecretStoreError) as captured:
        store.write_manager(SENTINEL + "\nunsafe")
    assert SENTINEL not in str(captured.value)


def test_symlink_destination_is_rejected(tmp_path: Path) -> None:
    if not hasattr(os, "symlink"):
        pytest.skip("symlinks are unavailable")
    paths = FactoryPaths.under(tmp_path)
    store = LocalFileSecretStore(paths)
    store.initialize()
    target = tmp_path / "target"
    target.write_text("do not replace", encoding="utf-8")
    destination = paths.secret_dir / "manager-token"
    try:
        destination.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation is unavailable to this user")
    with pytest.raises(SecretStoreError):
        store.write_manager(SENTINEL, overwrite=True)
    assert target.read_text(encoding="utf-8") == "do not replace"

