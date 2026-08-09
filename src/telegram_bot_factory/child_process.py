"""Low-privilege Telegram child process."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from telegram_bot_factory.models import (
    LeadInboxConfig,
    ProfileName,
    QuickFaqConfig,
)
from telegram_bot_factory.profile_store import ProfileStore
from telegram_bot_factory.profiles import (
    ChildProfile,
    LeadInboxProfile,
    LinkInboxProfile,
    OwnerEchoProfile,
    QuickFaqProfile,
)
from telegram_bot_factory.runtime import InstanceLauncher


def read_token_fd(descriptor: int) -> str:
    chunks: list[bytes] = []
    total = 0
    try:
        while True:
            chunk = os.read(descriptor, min(4096 - total, 1024))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total >= 4096:
                raise RuntimeError("Credential input is unexpectedly large.")
    finally:
        os.close(descriptor)
    value = b"".join(chunks).decode("utf-8")
    if not value or "\n" in value or "\r" in value:
        raise RuntimeError("Credential input is invalid.")
    return value


def write_health(runtime_dir: Path, status: str) -> None:
    target = runtime_dir / "health.json"
    temporary = runtime_dir / ".health.pending"
    temporary.write_text(json.dumps({"status": status}) + "\n", encoding="utf-8")
    temporary.chmod(0o600)
    os.replace(temporary, target)


async def run_child(token_fd: int, manifest_path: Path, runtime_dir: Path) -> None:
    manifest = InstanceLauncher.load_manifest(manifest_path)
    credential = read_token_fd(token_fd)
    bot = Bot(token=credential)
    credential = ""
    profile = build_profile(manifest, runtime_dir)
    store = ProfileStore(runtime_dir)
    offset = store.update_offset()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(signum, stop.set)
    write_health(
        runtime_dir,
        "reconciliation_required" if store.reconciliation_required() else "healthy",
    )
    try:
        while not stop.is_set():
            try:
                updates = await bot.get_updates(
                    offset=offset,
                    timeout=20,
                    allowed_updates=["message"],
                )
            except TelegramAPIError:
                await asyncio.sleep(1)
                continue
            for update in updates:
                offset = max(offset, update.update_id + 1)
                message = update.message
                if message is None or message.from_user is None or message.text is None:
                    store.advance_update_offset(update.update_id + 1)
                    continue
                disposition = await process_update(
                    store=store,
                    profile=profile,
                    update_id=update.update_id,
                    sender_telegram_id=message.from_user.id,
                    sender_chat_id=message.chat.id,
                    owner_telegram_id=manifest.owner_telegram_id,
                    text=message.text,
                    send_message=bot.send_message,
                )
                store.advance_update_offset(update.update_id + 1)
                if disposition == "quarantine":
                    write_health(runtime_dir, "reconciliation_required")
                    # A side effect may have happened. Stop this child rather than
                    # processing later messages under an ambiguous lifecycle.
                    break
    finally:
        write_health(
            runtime_dir,
            "reconciliation_required" if store.reconciliation_required() else "stopped",
        )
        await bot.session.close()


async def process_update(
    *,
    store: ProfileStore,
    profile: ChildProfile,
    update_id: int,
    sender_telegram_id: int,
    sender_chat_id: int,
    owner_telegram_id: int,
    text: str,
    send_message: Callable[[int, str], Awaitable[object]],
) -> str:
    disposition = store.begin_update(update_id)
    if disposition != "process":
        return disposition
    replies = profile.handle(sender_telegram_id, text)
    for reply in replies:
        target = sender_chat_id if reply.target == "sender" else owner_telegram_id
        await send_message(target, reply.text)
    store.complete_update(update_id)
    return "complete"


def build_profile(manifest: object, runtime_dir: Path) -> ChildProfile:
    from telegram_bot_factory.runtime import InstanceManifest

    if not isinstance(manifest, InstanceManifest):
        raise RuntimeError("Instance manifest is invalid.")
    if manifest.profile is ProfileName.OWNER_ECHO:
        return OwnerEchoProfile(manifest.owner_telegram_id, str(manifest.slug))
    if manifest.profile is ProfileName.QUICK_FAQ and isinstance(
        manifest.profile_config, QuickFaqConfig
    ):
        return QuickFaqProfile(manifest.profile_config)
    store = ProfileStore(runtime_dir)
    if manifest.profile is ProfileName.LEAD_INBOX and isinstance(
        manifest.profile_config, LeadInboxConfig
    ):
        return LeadInboxProfile(
            manifest.owner_telegram_id,
            manifest.profile_config.privacy_notice,
            store,
        )
    if manifest.profile is ProfileName.LINK_INBOX:
        return LinkInboxProfile(manifest.owner_telegram_id, store)
    raise RuntimeError("Unsupported child profile configuration.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bot-factory-child")
    parser.add_argument("--token-fd", type=int, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--runtime-dir", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    asyncio.run(run_child(arguments.token_fd, arguments.manifest, arguments.runtime_dir))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
