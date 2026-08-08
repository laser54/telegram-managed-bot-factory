"""Low-privilege Telegram child process."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
from collections.abc import Sequence
from pathlib import Path

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from telegram_bot_factory.models import ProfileName
from telegram_bot_factory.profiles import OwnerEchoProfile
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
    if manifest.profile is not ProfileName.OWNER_ECHO:
        raise RuntimeError("Unsupported child profile.")
    credential = read_token_fd(token_fd)
    bot = Bot(token=credential)
    credential = ""
    profile = OwnerEchoProfile(manifest.owner_telegram_id, str(manifest.slug))
    offset = 0
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(signum, stop.set)
    write_health(runtime_dir, "healthy")
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
                    continue
                reply = profile.handle(message.from_user.id, message.text)
                if reply is not None:
                    await bot.send_message(message.chat.id, reply.text)
    finally:
        write_health(runtime_dir, "stopped")
        await bot.session.close()


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

