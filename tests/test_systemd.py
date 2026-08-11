from pathlib import Path

import pytest

from telegram_bot_factory.paths import FactoryPaths
from telegram_bot_factory.systemd import (
    SystemdInstallError,
    ensure_user_lingering,
    ensure_user_systemd_available,
    render_user_unit,
    user_service_is_ready,
    verify_user_service_active,
)


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


def test_systemd_preflight_checks_user_manager_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def run(command: list[str], **kwargs: object) -> object:
        calls.append(command)
        return object()

    monkeypatch.setattr("telegram_bot_factory.systemd.shutil.which", lambda _: "/usr/bin/systemctl")
    monkeypatch.setattr("telegram_bot_factory.systemd.subprocess.run", run)

    ensure_user_systemd_available()

    assert calls == [["/usr/bin/systemctl", "--user", "show-environment"]]


def test_user_lingering_is_enabled_before_terminal_can_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    linger_checks = iter(["no\n", "yes\n"])

    def run(command: list[str], **kwargs: object) -> object:
        del kwargs
        calls.append(command)
        if command[1] == "show-user":
            return type("Result", (), {"stdout": next(linger_checks)})()
        return object()

    monkeypatch.setattr("telegram_bot_factory.systemd.shutil.which", lambda _: "/usr/bin/loginctl")
    monkeypatch.setattr("telegram_bot_factory.systemd.subprocess.run", run)
    monkeypatch.setattr("telegram_bot_factory.systemd.getpass.getuser", lambda: "root")

    ensure_user_lingering()

    assert calls == [
        ["/usr/bin/loginctl", "show-user", "root", "-p", "Linger", "--value"],
        ["/usr/bin/loginctl", "enable-linger", "root"],
        ["/usr/bin/loginctl", "show-user", "root", "-p", "Linger", "--value"],
    ]


def test_user_service_readiness_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    def inactive() -> None:
        raise SystemdInstallError("inactive")

    monkeypatch.setattr(
        "telegram_bot_factory.systemd.verify_user_service_active",
        inactive,
    )

    assert user_service_is_ready() is False


def test_worker_verification_requires_active_systemd_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def run(command: list[str], **kwargs: object) -> object:
        calls.append(command)
        return object()

    monkeypatch.setattr("telegram_bot_factory.systemd.shutil.which", lambda _: "/usr/bin/systemctl")
    monkeypatch.setattr("telegram_bot_factory.systemd.subprocess.run", run)

    verify_user_service_active()

    assert calls == [
        [
            "/usr/bin/systemctl",
            "--user",
            "is-active",
            "--quiet",
            "bot-factory-manager.service",
        ],
        [
            "/usr/bin/systemctl",
            "--user",
            "is-enabled",
            "--quiet",
            "bot-factory-manager.service",
        ],
    ]
