from pathlib import Path
from types import SimpleNamespace

import pytest

import telegram_bot_factory.setup as factory_setup
from telegram_bot_factory.config import read_factory_config
from telegram_bot_factory.paths import FactoryPaths
from telegram_bot_factory.secrets import LocalFileSecretStore
from tests.sentinels import token_shaped_sentinel

SENTINEL = token_shaped_sentinel("TEST_SENTINEL_MANAGER")


class FakeSession:
    async def close(self) -> None:
        return None


class FakeSetupBot:
    def __init__(self, token: str) -> None:
        assert token == SENTINEL
        self.session = FakeSession()
        self.calls = 0

    async def get_me(self) -> object:
        return SimpleNamespace(
            username="factory_manager_bot",
            can_manage_bots=True,
            id=100,
        )

    async def get_updates(self, **kwargs: object) -> list[object]:
        del kwargs
        self.calls += 1
        if self.calls == 1:
            return []
        user = SimpleNamespace(id=42, username="owner", full_name="Owner")
        chat = SimpleNamespace(type="private")
        message = SimpleNamespace(
            from_user=user,
            chat=chat,
            text="/claim claimcode",
        )
        return [SimpleNamespace(update_id=10, message=message)]


@pytest.mark.asyncio
async def test_setup_accepts_manager_credential_only_through_hidden_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = FactoryPaths.under(tmp_path)
    monkeypatch.setattr(factory_setup.getpass, "getpass", lambda _prompt: SENTINEL)
    monkeypatch.setattr(factory_setup.random_secrets, "token_urlsafe", lambda _size: "claimcode")
    monkeypatch.setattr(factory_setup, "Bot", FakeSetupBot)
    monkeypatch.setattr("builtins.input", lambda _prompt: "y")

    await factory_setup.run_setup(paths)

    config = read_factory_config(paths.config_dir / "config.json")
    assert config.owner_allowlist == [42]
    assert config.manager_username == "factory_manager_bot"
    assert LocalFileSecretStore(paths).read_manager() == SENTINEL
    assert SENTINEL.encode() not in (paths.config_dir / "config.json").read_bytes()


@pytest.mark.asyncio
async def test_setup_reuses_existing_secret_without_prompt_or_owner_polling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = FactoryPaths.under(tmp_path)
    monkeypatch.setattr(factory_setup.getpass, "getpass", lambda _prompt: SENTINEL)
    monkeypatch.setattr(factory_setup.random_secrets, "token_urlsafe", lambda _size: "claimcode")
    monkeypatch.setattr(factory_setup, "Bot", FakeSetupBot)
    monkeypatch.setattr("builtins.input", lambda _prompt: "y")
    await factory_setup.run_setup(paths)

    def unexpected_prompt(_prompt: str) -> str:
        raise AssertionError("idempotent setup must not prompt for the token")

    async def unexpected_enrollment(_bot: object, poll_timeout_seconds: int = 20) -> int:
        del poll_timeout_seconds
        raise AssertionError("idempotent setup must not poll for owner enrollment")

    monkeypatch.setattr(factory_setup.getpass, "getpass", unexpected_prompt)
    monkeypatch.setattr(factory_setup, "enroll_owner", unexpected_enrollment)

    await factory_setup.run_setup(paths)

    config = read_factory_config(paths.config_dir / "config.json")
    assert config.owner_allowlist == [42]
    assert LocalFileSecretStore(paths).read_manager() == SENTINEL
