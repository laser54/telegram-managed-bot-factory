"""Secure terminal-only first-run onboarding outside the agent conversation."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from telegram_bot_factory.paths import FactoryPaths
from telegram_bot_factory.setup import setup_main
from telegram_bot_factory.state import FactoryState
from telegram_bot_factory.systemd import (
    ensure_user_lingering,
    ensure_user_systemd_available,
    install_user_service,
    verify_user_service_active,
)


class OnboardingError(RuntimeError):
    """Safe first-run onboarding failure."""



def verify_worker_heartbeat(
    paths: FactoryPaths,
    not_before: datetime | None = None,
    *,
    timeout_seconds: float = 30.0,
) -> None:
    """Wait for the systemd worker to prove it completed startup and entered its loop."""
    state = FactoryState(paths.database_path)
    deadline = time.monotonic() + max(timeout_seconds, 0.0)
    freshness = timedelta(seconds=30)
    while True:
        heartbeat = state.worker_heartbeat()
        if (
            heartbeat is not None
            and datetime.now(UTC) - heartbeat <= freshness
            and (not_before is None or heartbeat >= not_before)
        ):
            return
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise OnboardingError(
                "The Factory worker service started but did not report a healthy heartbeat."
            )
        time.sleep(min(0.25, remaining))


def run_onboarding(manager: Path, paths: FactoryPaths | None = None) -> None:
    """Run local setup and install the mandatory persistent systemd worker."""
    trusted_paths = paths or FactoryPaths.discover()
    ensure_user_systemd_available()
    ensure_user_lingering()
    setup_main(trusted_paths)
    service_start = datetime.now(UTC)
    install_user_service(manager, trusted_paths)
    verify_user_service_active()
    verify_worker_heartbeat(trusted_paths, service_start)
    print("Factory worker is installed, active, and healthy under systemd --user.")
    print("Hermes registration continues in this terminal. Never paste credentials into chat.")
