"""Operator command line entry point."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from telegram_bot_factory import __version__
from telegram_bot_factory.installer import InstallError, install_for_hermes


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bot-factory")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command")
    commands.add_parser(
        "install-hermes",
        help="Run complete terminal-only Factory installation on this Linux host",
        description=(
            "Run the complete terminal-only Factory installation on this Linux host. "
            "The manager token is requested through a hidden interactive prompt and "
            "must never be passed as an argument, environment variable, or chat message."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    if arguments.command == "install-hermes":
        try:
            install_for_hermes()
        except InstallError as error:
            print(f"Factory installation did not complete: {error}")
            return 1
        return 0
    parser.print_help()
    return 0
