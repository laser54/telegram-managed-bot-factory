"""Typed, redacted Telegram Bot API boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from urllib.parse import quote

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramNetworkError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class TelegramError(RuntimeError):
    """A safe Telegram failure that never includes response data or credentials."""


class TelegramAmbiguousError(TelegramError):
    """The external outcome is not safe to infer or retry."""


@dataclass(frozen=True, slots=True)
class ManagerIdentity:
    user_id: int
    username: str
    can_manage_bots: bool


@dataclass(frozen=True, slots=True)
class ManagedBotEvent:
    update_id: int
    owner_telegram_id: int
    child_user_id: int
    child_username: str


class TelegramGateway(Protocol):
    async def get_identity(self) -> ManagerIdentity: ...

    async def get_managed_events(
        self, offset: int, poll_timeout_seconds: int
    ) -> list[ManagedBotEvent]: ...

    async def get_managed_bot_token(self, child_user_id: int) -> str: ...

    async def send_confirmation(self, owner_telegram_id: int, confirmation_url: str) -> None: ...

    async def close(self) -> None: ...


def managed_bot_confirmation_url(
    manager_username: str, child_username: str, display_name: str
) -> str:
    return (
        f"https://t.me/newbot/{quote(manager_username, safe='')}/"
        f"{quote(child_username, safe='')}?name={quote(display_name, safe='')}"
    )


class AiogramTelegramGateway:
    def __init__(self, manager_token: str) -> None:
        try:
            self._bot = Bot(token=manager_token)
        except Exception as error:
            raise TelegramError("Manager credential is invalid.") from error

    async def get_identity(self) -> ManagerIdentity:
        try:
            user = await self._bot.get_me()
        except TelegramNetworkError as error:
            raise TelegramAmbiguousError(
                "Manager identity request had an unknown outcome."
            ) from error
        except TelegramAPIError as error:
            raise TelegramError("Manager identity request was rejected.") from error
        if not user.username:
            raise TelegramError("Manager bot has no username.")
        return ManagerIdentity(
            user_id=user.id,
            username=user.username,
            can_manage_bots=bool(user.can_manage_bots),
        )

    async def get_managed_events(
        self, offset: int, poll_timeout_seconds: int
    ) -> list[ManagedBotEvent]:
        try:
            updates = await self._bot.get_updates(
                offset=offset,
                timeout=poll_timeout_seconds,
                allowed_updates=["managed_bot"],
            )
        except TelegramAPIError as error:
            raise TelegramError("Manager update polling failed safely.") from error
        events: list[ManagedBotEvent] = []
        for update in updates:
            managed = update.managed_bot
            if managed is None or managed.bot_user.username is None:
                continue
            events.append(
                ManagedBotEvent(
                    update_id=update.update_id,
                    owner_telegram_id=managed.user.id,
                    child_user_id=managed.bot_user.id,
                    child_username=managed.bot_user.username,
                )
            )
        return events

    async def get_managed_bot_token(self, child_user_id: int) -> str:
        try:
            value = await self._bot.get_managed_bot_token(user_id=child_user_id)
        except TelegramNetworkError as error:
            raise TelegramAmbiguousError("Credential retrieval had an unknown outcome.") from error
        except TelegramAPIError as error:
            raise TelegramError("Credential retrieval was rejected.") from error
        if not value:
            raise TelegramError("Credential retrieval returned no credential.")
        return value

    async def send_confirmation(self, owner_telegram_id: int, confirmation_url: str) -> None:
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Create in Telegram", url=confirmation_url)]
            ]
        )
        try:
            await self._bot.send_message(
                chat_id=owner_telegram_id,
                text="Confirm creation of the requested managed bot in Telegram.",
                reply_markup=markup,
            )
        except TelegramNetworkError as error:
            raise TelegramAmbiguousError("Owner notification had an unknown outcome.") from error
        except TelegramAPIError as error:
            raise TelegramError("Owner notification was rejected.") from error

    async def close(self) -> None:
        await self._bot.session.close()
