"""Operator command line entry point."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from telegram_bot_factory import __version__
from telegram_bot_factory.installer import InstallError, install_for_hermes
from telegram_bot_factory.onboarding import onboard_main
from telegram_bot_factory.setup import SetupError, setup_main


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bot-factory")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("setup", help="Configure a manager through a hidden local prompt")
    onboard = commands.add_parser(
        "onboard",
        help="Configure the manager and install the mandatory systemd --user worker",
        description="Configure the manager and install the mandatory systemd --user worker.",
    )
    onboard.add_argument(
        "--hold",
        action="store_true",
        help="Wait for Enter before closing a terminal opened by Hermes Desktop",
    )
    commands.add_parser("install-hermes", help="Install the Factory and register it in Hermes")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    if arguments.command == "setup":
        try:
            setup_main()
        except SetupError as error:
            print(f"Factory setup did not start: {error}")
            return 1
        return 0
    if arguments.command == "onboard":
        return onboard_main(hold=bool(arguments.hold))
    if arguments.command == "install-hermes":
        try:
            install_for_hermes()
        except InstallError as error:
            print(f"Factory installation did not complete: {error}")
            return 1
        return 0
    parser.print_help()
    return 0
