import json
from pathlib import Path

from telegram_bot_factory import __version__
from telegram_bot_factory.cli import main


def test_package_version() -> None:
    assert __version__ == "0.1.1"


def test_release_metadata_matches_package_version() -> None:
    root = Path(__file__).parents[1]
    server = json.loads((root / "server.json").read_text(encoding="utf-8"))

    assert server["version"] == __version__
    assert server["packages"][0]["version"] == __version__
    assert f"## [{__version__}] - 2026-08-09" in (root / "CHANGELOG.md").read_text(
        encoding="utf-8"
    )


def test_cli_help(capsys: object) -> None:
    assert main([]) == 0
