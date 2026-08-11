"""Interactive local setup that keeps the manager credential outside MCP."""

from __future__ import annotations

import asyncio
import getpass
import secrets as random_secrets
import sys

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from telegram_bot_factory.config import (
    FactoryConfig,
    read_factory_config,
    write_factory_config,
)
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
    store = LocalFileSecretStore(trusted_paths)
    config_path = trusted_paths.config_dir / "config.json"
    has_secret = store.manager_configured()
    has_config = config_path.is_file()
    if has_secret != has_config:
        raise SetupError("Existing Factory setup is incomplete and requires reconciliation.")
    existing_config = read_factory_config(config_path) if has_config else None
    credential = (
        store.read_manager()
        if has_secret
        else getpass.getpass("Manager token (hidden): ")
    )
    bot: Bot | None = None
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
        if existing_config is None:
            owner_id = await enroll_owner(bot)
            store.write_manager(credential)
            write_factory_config(
                config_path,
                FactoryConfig(
                    manager_username=identity.username,
                    manager_user_id=identity.id,
                    can_manage_bots=True,
                    owner_allowlist=[owner_id],
                ),
            )
        elif (
            identity.username != existing_config.manager_username
            or identity.id != existing_config.manager_user_id
        ):
            raise SetupError("Stored manager identity does not match Telegram.")
        FactoryState(trusted_paths.database_path).initialize()
    finally:
        credential = ""
        if bot is not None:
            await bot.session.close()
    print(
        "Factory setup verified. The manager credential remains stored locally "
        "with owner-only access."
    )
    print(
        "No child bots were created. Create a test or useful child only through "
        "an explicit Factory request and Telegram confirmation."
    )


def setup_main(paths: FactoryPaths | None = None) -> None:
    if not sys.stdin.isatty():
        raise SetupError(
            "Local setup requires an interactive terminal on this Linux host. Run "
            "'bot-factory install-hermes'; never send the manager credential through chat "
            "or piped input."
        )
    asyncio.run(run_setup(paths))
