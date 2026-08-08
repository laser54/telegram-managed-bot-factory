"""Interactive local setup that keeps the manager credential outside MCP."""

from __future__ import annotations

import asyncio
import getpass
import secrets as random_secrets

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from telegram_bot_factory.config import FactoryConfig, write_factory_config
from telegram_bot_factory.paths import FactoryPaths
from telegram_bot_factory.secrets import LocalFileSecretStore
from telegram_bot_factory.state import FactoryState


class SetupError(RuntimeError):
    """Safe setup failure."""


async def enroll_owner(bot: Bot, poll_timeout_seconds: int = 20) -> int:
    code = random_secrets.token_urlsafe(6)
    print("Send this one-time command to the manager bot in a private chat:")
    print(f"/claim {code}")
    try:
        existing = await bot.get_updates(offset=-1, timeout=0, allowed_updates=["message"])
    except TelegramAPIError as error:
        raise SetupError("Owner enrollment could not start safely.") from error
    offset = 0 if not existing else max(update.update_id for update in existing) + 1
    for _ in range(15):
        try:
            updates = await bot.get_updates(
                offset=offset,
                timeout=poll_timeout_seconds,
                allowed_updates=["message"],
            )
        except TelegramAPIError as error:
            raise SetupError("Owner enrollment polling failed safely.") from error
        for update in updates:
            offset = max(offset, update.update_id + 1)
            message = update.message
            if (
                message is None
                or message.from_user is None
                or message.chat.type != "private"
                or message.text != f"/claim {code}"
            ):
                continue
            label = message.from_user.username or message.from_user.full_name
            answer = await asyncio.to_thread(
                input, f"Authorize Telegram account {label!r} as owner? [y/N]: "
            )
            if answer.strip().casefold() not in {"y", "yes"}:
                raise SetupError("Owner enrollment was not confirmed locally.")
            return message.from_user.id
    raise SetupError("Owner enrollment timed out.")


async def run_setup(paths: FactoryPaths | None = None) -> None:
    trusted_paths = paths or FactoryPaths.discover()
    trusted_paths.ensure_non_secret_layout()
    credential = getpass.getpass("Manager token (hidden): ")
    try:
        bot = Bot(token=credential)
    except Exception as error:
        raise SetupError("Manager credential is invalid.") from error
    try:
        try:
            identity = await bot.get_me()
        except TelegramAPIError as error:
            raise SetupError("Manager identity could not be verified.") from error
        if not identity.username:
            raise SetupError("Manager bot must have a username.")
        if not identity.can_manage_bots:
            raise SetupError("Enable Bot Management Mode in BotFather before setup.")
        owner_id = await enroll_owner(bot)
        store = LocalFileSecretStore(trusted_paths)
        store.write_manager(credential, overwrite=store.manager_configured())
        write_factory_config(
            trusted_paths.config_dir / "config.json",
            FactoryConfig(
                manager_username=identity.username,
                manager_user_id=identity.id,
                can_manage_bots=True,
                owner_allowlist=[owner_id],
            ),
        )
        FactoryState(trusted_paths.database_path).initialize()
    finally:
        credential = ""
        await bot.session.close()
    print(
        "Factory setup verified. The manager credential is stored locally "
        "with owner-only access."
    )


def setup_main(paths: FactoryPaths | None = None) -> None:
    asyncio.run(run_setup(paths))
