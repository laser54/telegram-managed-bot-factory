"""Persistent manager worker entry point."""

from __future__ import annotations

import argparse
import asyncio
import signal
from collections.abc import Sequence

from telegram_bot_factory.config import read_factory_config
from telegram_bot_factory.models import RequestState
from telegram_bot_factory.paths import FactoryPaths
from telegram_bot_factory.runtime import InstanceLauncher, RuntimeProvisionError
from telegram_bot_factory.secrets import LocalFileSecretStore
from telegram_bot_factory.state import FactoryState, StateError
from telegram_bot_factory.telegram import AiogramTelegramGateway, TelegramError
from telegram_bot_factory.worker import ManagerWorker


async def run_manager() -> None:
    paths = FactoryPaths.discover()
    config = read_factory_config(paths.config_dir / "config.json")
    state = FactoryState(paths.database_path)
    secret_store = LocalFileSecretStore(paths)
    manager_credential = secret_store.read_manager()
    telegram = AiogramTelegramGateway(manager_credential)
    manager_credential = ""
    launcher = InstanceLauncher(paths, secret_store)
    worker = ManagerWorker(state, secret_store, telegram, launcher)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(signum, stop.set)
    preflight = await worker.preflight()
    if preflight.manager_username.casefold() != config.manager_username.casefold():
        raise RuntimeError("Configured manager identity does not match the credential.")
    recover_active_instances(state, launcher, paths)
    try:
        while not stop.is_set():
            state.set_worker_heartbeat()
            await worker.dispatch_pending_notifications()
            try:
                await worker.poll_once(poll_timeout_seconds=5)
            except TelegramError:
                await asyncio.sleep(1)
            process_runtime_commands(state, launcher, paths)
    finally:
        launcher.shutdown()
        await worker.close()


def process_runtime_commands(
    state: FactoryState, launcher: InstanceLauncher, paths: FactoryPaths
) -> None:
    for command in state.pending_runtime_commands():
        instance = state.get_instance(str(command.slug))
        if instance is None:
            state.complete_runtime_command(command.command_id, succeeded=False)
            continue
        request = state.get_request(instance.request_id)
        if request is None:
            state.complete_runtime_command(command.command_id, succeeded=False)
            continue
        try:
            if command.action == "stop":
                launcher.stop(command.slug)
                state.transition(request.request_id, RequestState.STOPPED)
                state.update_instance_lifecycle(
                    str(command.slug), RequestState.STOPPED, "stopped"
                )
            else:
                manifest_path = paths.instance_dir / str(command.slug) / "manifest.json"
                launcher.start(launcher.load_manifest(manifest_path))
                state.transition(request.request_id, RequestState.ACTIVE)
                state.update_instance_lifecycle(
                    str(command.slug), RequestState.ACTIVE, "healthy"
                )
            state.complete_runtime_command(command.command_id, succeeded=True)
        except (RuntimeProvisionError, StateError):
            state.complete_runtime_command(command.command_id, succeeded=False)


def recover_active_instances(
    state: FactoryState, launcher: InstanceLauncher, paths: FactoryPaths
) -> None:
    for instance in state.list_instances():
        if instance.state is not RequestState.ACTIVE:
            continue
        manifest_path = paths.instance_dir / str(instance.slug) / "manifest.json"
        try:
            launcher.start(launcher.load_manifest(manifest_path))
        except RuntimeProvisionError:
            request = state.get_request(instance.request_id)
            if request is not None and request.state is RequestState.ACTIVE:
                state.transition(request.request_id, RequestState.STOPPED, "restart_failed")
            state.update_instance_lifecycle(
                str(instance.slug), RequestState.STOPPED, "failed"
            )

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bot-factory-manager")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("run", help="Run the persistent Telegram manager worker")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    if arguments.command == "run":
        asyncio.run(run_manager())
        return 0
    parser.print_help()
    return 0
