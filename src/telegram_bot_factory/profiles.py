"""Deterministic child profile behavior independent from Telegram transport."""

from __future__ import annotations

from dataclasses import dataclass

from telegram_bot_factory import __version__


@dataclass(frozen=True, slots=True)
class ProfileReply:
    text: str


class OwnerEchoProfile:
    name = "owner_echo"

    def __init__(self, owner_telegram_id: int, instance_slug: str) -> None:
        self._owner = owner_telegram_id
        self._slug = instance_slug

    def handle(self, sender_telegram_id: int, text: str) -> ProfileReply | None:
        if sender_telegram_id != self._owner:
            return None
        command = text.split("@", 1)[0].strip()
        if command == "/start":
            return ProfileReply("Owner Echo is ready. Use /help or /health.")
        if command == "/help":
            return ProfileReply("Commands: /start, /help, /health. Other text is echoed.")
        if command == "/health":
            return ProfileReply(f"OK · profile={self.name} · version={__version__}")
        bounded = text[:4000]
        return ProfileReply(f"{self._slug}: {bounded}")

