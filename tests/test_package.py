import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from telegram_bot_factory import __version__
from telegram_bot_factory.cli import main


def test_package_version() -> None:
    assert __version__ == "0.2.3"


def test_release_metadata_matches_package_version() -> None:
    root = Path(__file__).parents[1]
    server = json.loads((root / "server.json").read_text(encoding="utf-8"))

    assert server["version"] == __version__
    assert server["packages"][0]["version"] == __version__
    assert f"## [{__version__}] - 2026-08-22" in (root / "CHANGELOG.md").read_text(
        encoding="utf-8"
    )
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert f"PyPI%20release-{__version__}" in readme
    assert f"Version `{__version__}` is terminal-only: no Desktop bootstrap exists." in readme
    assert f"uvx --refresh --from telegram-managed-bot-factory=={__version__}" in readme
    assert f"unreleased `{__version__}`" not in readme


def test_cli_help(capsys: object) -> None:
    assert main([]) == 0


def test_cli_exposes_one_terminal_only_install_command(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_result:
        main(["install-hermes", "--help"])
    assert exit_result.value.code == 0
    output = capsys.readouterr().out.casefold()
    assert "terminal" in output
    assert "desktop" not in output


def test_cli_reports_installer_failure_without_traceback(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from telegram_bot_factory.installer import InstallError

    monkeypatch.setattr(
        "telegram_bot_factory.cli.install_for_hermes",
        Mock(side_effect=InstallError("systemd --user is unavailable.")),
    )

    assert main(["install-hermes"]) == 1
    output = capsys.readouterr().out
    assert "systemd --user is unavailable" in output
    assert "Traceback" not in output
