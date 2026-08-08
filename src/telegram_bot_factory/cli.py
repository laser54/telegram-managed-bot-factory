"""Operator command line entry point."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from telegram_bot_factory import __version__
from telegram_bot_factory.installer import install_for_hermes
from telegram_bot_factory.setup import setup_main


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bot-factory")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("setup", help="Configure a manager through a hidden local prompt")
    commands.add_parser("install-hermes", help="Install the Factory and register it in Hermes")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    if arguments.command == "setup":
        setup_main()
        return 0
    if arguments.command == "install-hermes":
        install_for_hermes()
        return 0
    parser.print_help()
    return 0
