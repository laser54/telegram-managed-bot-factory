
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

import telegram_bot_factory.onboarding as onboarding
from telegram_bot_factory.paths import FactoryPaths
from telegram_bot_factory.state import FactoryState


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
