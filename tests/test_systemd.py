from pathlib import Path

import pytest

from telegram_bot_factory.paths import FactoryPaths
from telegram_bot_factory.systemd import SystemdInstallError, render_user_unit


def test_systemd_unit_contains_hardening_and_no_credentials(tmp_path: Path) -> None:
    paths = FactoryPaths.under(tmp_path)
    manager = (tmp_path / "bin" / "bot-factory-manager").resolve()
    unit = render_user_unit(manager, paths)
    assert "NoNewPrivileges=true" in unit
    assert "PrivateTmp=true" in unit
    assert "ProtectSystem=strict" in unit
    assert "ProtectHome=read-only" in unit
    assert "PrivateDevices=" not in unit
    assert "BOT_FACTORY_MANAGER_TOKEN" not in unit
    assert "Environment=" not in unit


def test_systemd_rejects_relative_executable(tmp_path: Path) -> None:
    with pytest.raises(SystemdInstallError, match="absolute"):
        render_user_unit(Path("bin/bot-factory-manager"), FactoryPaths.under(tmp_path))
