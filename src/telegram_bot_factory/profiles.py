"""Deterministic child profile behavior independent from Telegram transport."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Literal, Protocol

from telegram_bot_factory import __version__
from telegram_bot_factory.models import QuickFaqConfig
from telegram_bot_factory.profile_store import ProfileStore


@dataclass(frozen=True, slots=True)
class ProfileReply:
    text: str
    target: Literal["sender", "owner"] = "sender"


class ChildProfile(Protocol):
    def handle(self, sender_telegram_id: int, text: str) -> list[ProfileReply]: ...


class OwnerEchoProfile:
    name = "owner_echo"

    def __init__(self, owner_telegram_id: int, instance_slug: str) -> None:
        self._owner = owner_telegram_id
        self._slug = instance_slug

    def handle(self, sender_telegram_id: int, text: str) -> list[ProfileReply]:
        if sender_telegram_id != self._owner:
            return []
        command = text.split("@", 1)[0].strip()
        if command == "/start":
            return [ProfileReply("Owner Echo is ready. Use /help or /health.")]
        if command == "/help":
            return [ProfileReply("Commands: /start, /help, /health. Other text is echoed.")]
        if command == "/health":
            return [ProfileReply(f"OK · profile={self.name} · version={__version__}")]
        bounded = text[:4000]
        return [ProfileReply(f"{self._slug}: {bounded}")]


class QuickFaqProfile:
    name = "quick_faq"

    def __init__(self, config: QuickFaqConfig) -> None:
        self._config = config

    def handle(self, sender_telegram_id: int, text: str) -> list[ProfileReply]:
        del sender_telegram_id
        command = text.split("@", 1)[0].strip()
        if command == "/health":
            return [ProfileReply(f"OK · profile={self.name} · version={__version__}")]
        if command in {"/start", "/help"}:
            menu = "\n".join(
                f"{index}. {entry.question}"
                for index, entry in enumerate(self._config.faqs, start=1)
            )
            return [
                ProfileReply(
                    f"{self._config.welcome}\n\n{menu}\n\n"
                    "Send /faq N for an answer or /contact."
                )
            ]
        if command == "/contact":
            return [ProfileReply(self._config.contact_text)]
        if command.startswith("/faq "):
            raw_index = command.removeprefix("/faq ").strip()
            if raw_index.isdigit():
                index = int(raw_index) - 1
                if 0 <= index < len(self._config.faqs):
                    entry = self._config.faqs[index]
                    return [ProfileReply(f"{entry.question}\n\n{entry.answer}")]
        return [ProfileReply("Choose an item with /faq N, or use /contact.")]


class LeadInboxProfile:
    name = "lead_inbox"

    def __init__(self, owner_telegram_id: int, privacy_notice: str, store: ProfileStore) -> None:
        self._owner = owner_telegram_id
        self._notice = privacy_notice
        self._store = store

    def handle(self, sender_telegram_id: int, text: str) -> list[ProfileReply]:
        command = text.split("@", 1)[0].strip()
        if sender_telegram_id == self._owner and command.startswith("/export"):
            return self._export(command)
        if sender_telegram_id == self._owner and command.startswith("/purge"):
            return self._purge(command)
        if command == "/health":
            return [ProfileReply(f"OK · profile={self.name} · version={__version__}")]
        if command in {"/start", "/help"}:
            self._store.set_conversation(sender_telegram_id, "name", None)
            return [
                ProfileReply(
                    f"{self._notice}\n\nSend your name, or /skip to continue without it."
                )
            ]
        conversation = self._store.conversation(sender_telegram_id)
        if conversation is None:
            return [ProfileReply("Use /start to submit a message.")]
        stage, optional_name = conversation
        bounded = text.strip()[:2000]
        if stage == "name":
            name = None if command == "/skip" else bounded[:100]
            self._store.set_conversation(sender_telegram_id, "message", name)
            return [ProfileReply("Send your message (maximum 2000 characters).")]
        if not bounded:
            return [ProfileReply("Message cannot be empty.")]
        lead_id = self._store.add_lead(sender_telegram_id, optional_name, bounded)
        self._store.clear_conversation(sender_telegram_id)
        summary_name = optional_name or "Not provided"
        return [
            ProfileReply("Thank you. Your message was saved for the owner."),
            ProfileReply(
                f"New lead #{lead_id}\nName: {summary_name}\nMessage: {bounded}",
                target="owner",
            ),
        ]

    def _export(self, command: str) -> list[ProfileReply]:
        if command != "/export confirm":
            return [ProfileReply("Send /export confirm to export stored leads.")]
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["lead_id", "name", "message"])
        rows = (
            (lead_id, name or "", message)
            for lead_id, name, message in self._store.leads()
        )
        writer.writerows(rows)
        return [ProfileReply(output.getvalue()[:4000])]

    def _purge(self, command: str) -> list[ProfileReply]:
        if command != "/purge confirm":
            return [ProfileReply("Send /purge confirm to permanently remove stored leads.")]
        count = self._store.purge_leads()
        return [ProfileReply(f"Purged {count} stored lead records.")]


class LinkInboxProfile:
    name = "link_inbox"

    def __init__(self, owner_telegram_id: int, store: ProfileStore) -> None:
        self._owner = owner_telegram_id
        self._store = store

    def handle(self, sender_telegram_id: int, text: str) -> list[ProfileReply]:
        if sender_telegram_id != self._owner:
            return []
        command = text.split("@", 1)[0].strip()
        if command == "/health":
            return [ProfileReply(f"OK · profile={self.name} · version={__version__}")]
        if command in {"/start", "/help"}:
            return [ProfileReply("Send a URL or note. Use /list and /done N.")]
        if command == "/list":
            items = self._store.pending_links()
            if not items:
                return [ProfileReply("Inbox is empty.")]
            return [ProfileReply("\n".join(f"{item_id}. {content}" for item_id, content in items))]
        if command.startswith("/done "):
            raw_id = command.removeprefix("/done ").strip()
            if raw_id.isdigit() and self._store.complete_link(int(raw_id)):
                return [ProfileReply(f"Completed item {raw_id}.")]
            return [ProfileReply("Unknown pending item.")]
        bounded = text.strip()[:2000]
        if not bounded:
            return [ProfileReply("Note cannot be empty.")]
        item_id = self._store.add_link(bounded)
        return [ProfileReply(f"Saved item {item_id}. No URL was opened or fetched.")]
