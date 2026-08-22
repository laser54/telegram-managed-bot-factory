from pathlib import Path
from unittest.mock import patch

import pytest

from telegram_bot_factory.installer import (
    InstallError,
    _hermes_test_verified,
    _register_hermes,
    install_for_hermes,
)


def test_hermes_result_requires_exact_nine_tool_success() -> None:
    assert _hermes_test_verified("Connected\nTools discovered: 9") is True
    assert _hermes_test_verified("Connection failed\nTools discovered: 0") is False
    assert _hermes_test_verified("Connected\nTools discovered: 6") is False


def test_hermes_add_keeps_required_interactive_confirmation_visible() -> None:
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
    )


def test_non_posix_install_error_is_version_agnostic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("telegram_bot_factory.installer.os.name", "nt")

    with pytest.raises(InstallError, match="Factory installation supports Linux only"):
        install_for_hermes()
