import subprocess
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

import telegram_bot_factory.onboarding as onboarding
from telegram_bot_factory import __version__
from telegram_bot_factory.paths import FactoryPaths
from telegram_bot_factory.state import FactoryState
from telegram_bot_factory.systemd import SystemdInstallError


def test_terminal_launcher_opens_onboarding_without_secret_channels(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    operator = tmp_path / "bin" / "bot-factory"
    operator.parent.mkdir()
    operator.touch()
    popen = Mock()
    monkeypatch.setattr(onboarding, "_operator_executable", lambda: operator)
    monkeypatch.setattr(
        onboarding,
        "_terminal_command",
        lambda command: ["/usr/bin/xdg-terminal-exec", *command],
    )
    monkeypatch.setattr(
        onboarding,
        "_terminal_environment",
        lambda: {"HOME": "/home/test", "DISPLAY": ":1"},
    )
    monkeypatch.setattr("telegram_bot_factory.onboarding.subprocess.Popen", popen)

    result = onboarding.launch_setup_terminal()

    assert result.launched is True
    assert result.status == "setup_terminal_opened"
    popen.assert_called_once_with(
        ["/usr/bin/xdg-terminal-exec", str(operator), "onboard", "--hold"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        start_new_session=True,
        env={"HOME": "/home/test", "DISPLAY": ":1"},
    )
    rendered_call = repr(popen.call_args).casefold()
    assert "token" not in rendered_call
    assert "credential" not in rendered_call
    assert set(popen.call_args.kwargs["env"]) == {"HOME", "DISPLAY"}


def test_terminal_environment_reconstructs_filtered_desktop_session_without_secrets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "bus").touch()
    (runtime / "wayland-0").touch()
    monkeypatch.setattr(
        "telegram_bot_factory.onboarding.os.environ",
        {
            "HOME": "/home/test",
            "PATH": "/usr/bin",
            "XDG_RUNTIME_DIR": str(runtime),
            "TELEGRAM_BOT_TOKEN": "must-not-cross",
        },
    )

    environment = onboarding._terminal_environment()

    assert environment["DBUS_SESSION_BUS_ADDRESS"] == f"unix:path={runtime / 'bus'}"
    assert environment["WAYLAND_DISPLAY"] == "wayland-0"
    assert "TELEGRAM_BOT_TOKEN" not in environment
    assert "must-not-cross" not in repr(environment)


def test_onboarding_checks_systemd_before_requesting_setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup = Mock()
    monkeypatch.setattr(onboarding, "ensure_user_systemd_available", Mock(side_effect=RuntimeError))
    monkeypatch.setattr(onboarding, "setup_main", setup)

    with pytest.raises(RuntimeError):
        onboarding.run_onboarding(
            (tmp_path / "bot-factory-manager").resolve(), FactoryPaths.under(tmp_path)
        )

    setup.assert_not_called()


def test_onboarding_installs_and_verifies_worker_after_local_setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    manager = (tmp_path / "bot-factory-manager").resolve()
    paths = FactoryPaths.under(tmp_path)
    monkeypatch.setattr(
        onboarding, "ensure_user_systemd_available", lambda: calls.append("preflight")
    )
    monkeypatch.setattr(onboarding, "setup_main", lambda _paths: calls.append("setup"))

    def install(_manager: Path, _paths: FactoryPaths) -> Path:
        calls.append("install")
        return tmp_path / "worker.service"

    monkeypatch.setattr(onboarding, "install_user_service", install)
    monkeypatch.setattr(
        onboarding, "verify_user_service_active", lambda: calls.append("verify")
    )
    monkeypatch.setattr(
        onboarding,
        "verify_worker_heartbeat",
        lambda _paths, _not_before: calls.append("heartbeat"),
    )

    onboarding.run_onboarding(manager, paths)

    assert calls == ["preflight", "setup", "install", "verify", "heartbeat"]


def test_worker_heartbeat_verification_accepts_fresh_persistent_worker(tmp_path: Path) -> None:
    paths = FactoryPaths.under(tmp_path)
    FactoryState(paths.database_path).set_worker_heartbeat()

    onboarding.verify_worker_heartbeat(paths, timeout_seconds=0)


def test_worker_heartbeat_verification_rejects_stale_other_worker(
    tmp_path: Path,
) -> None:
    paths = FactoryPaths.under(tmp_path)
    state = FactoryState(paths.database_path)
    state.set_worker_heartbeat()
    service_start = datetime.now(UTC)

    with pytest.raises(onboarding.OnboardingError, match="healthy heartbeat"):
        onboarding.verify_worker_heartbeat(paths, service_start, timeout_seconds=0)


def test_stable_worker_install_is_pinned_and_returns_persistent_manager(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manager = tmp_path / "bin" / "bot-factory-manager"
    manager.parent.mkdir()
    manager.touch()
    calls: list[list[str]] = []

    def run(command: list[str], **kwargs: object) -> object:
        calls.append(command)
        if command[-3:] == ["tool", "dir", "--bin"]:
            return type("Result", (), {"stdout": str(manager.parent)})()
        return object()

    monkeypatch.setattr(
        "telegram_bot_factory.onboarding.shutil.which", lambda name: f"/usr/bin/{name}"
    )
    monkeypatch.setattr("telegram_bot_factory.onboarding.subprocess.run", run)

    installed = onboarding.install_stable_worker()

    assert installed == manager.resolve()
    assert calls[0] == [
        "/usr/bin/uv",
        "tool",
        "install",
        "--force",
        f"telegram-managed-bot-factory=={__version__}",
    ]
    assert calls[1] == ["/usr/bin/uv", "tool", "dir", "--bin"]


def test_onboard_main_reports_safe_failure_and_holds_terminal(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(onboarding, "install_stable_worker", lambda: Path("/worker"))
    monkeypatch.setattr(
        onboarding,
        "run_onboarding",
        Mock(side_effect=SystemdInstallError("systemd --user is unavailable.")),
    )
    held: list[str] = []

    def hold(prompt: str) -> str:
        held.append(prompt)
        return ""

    monkeypatch.setattr("builtins.input", hold)

    result = onboarding.onboard_main(hold=True)

    assert result == 1
    assert held == ["Press Enter to close this terminal..."]
    output = capsys.readouterr().out
    assert "systemd --user is unavailable" in output
    assert "Traceback" not in output
