"""Telegram Managed Bot Factory."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("telegram-managed-bot-factory")
except PackageNotFoundError:  # pragma: no cover - source tree without installation
    __version__ = "0.2.2"

__all__ = ["__version__"]
