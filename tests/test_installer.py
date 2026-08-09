from pathlib import Path
from unittest.mock import patch

from telegram_bot_factory.installer import _hermes_test_verified, _register_hermes


def test_hermes_result_requires_exact_six_tool_success() -> None:
    assert _hermes_test_verified("Connected\nTools discovered: 6") is True
    assert _hermes_test_verified("Connection failed\nTools discovered: 0") is False
    assert _hermes_test_verified("Connected\nTools discovered: 5") is False


def test_hermes_add_uses_direct_cli_arguments_without_stdin() -> None:
    with patch("telegram_bot_factory.installer.subprocess.run") as run:
        _register_hermes("/usr/bin/hermes", Path("/opt/factory/bot-factory-mcp"))

    run.assert_called_once_with(
        [
            "/usr/bin/hermes",
            "mcp",
            "add",
            "bot-factory",
            "--command",
            "/opt/factory/bot-factory-mcp",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
