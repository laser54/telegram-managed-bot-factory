"""Secure first-run onboarding launched outside the agent conversation."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from telegram_bot_factory import __version__
from telegram_bot_factory.models import StrictModel
from telegram_bot_factory.paths import FactoryPaths
from telegram_bot_factory.setup import SetupError, setup_main
from telegram_bot_factory.state import FactoryState
from telegram_bot_factory.systemd import (
    SystemdInstallError,
    ensure_user_systemd_available,
    install_user_service,
    verify_user_service_active,
)


class OnboardingError(RuntimeError):
    """Safe first-run onboarding failure."""


class OnboardingLaunchResult(StrictModel):
    launched: bool
    status: Literal["setup_terminal_opened"]
    next_action: str


def _operator_executable() -> Path:
    sibling = Path(sys.executable).resolve().with_name("bot-factory")
    if sibling.is_file():
        return sibling
    discovered = shutil.which("bot-factory")
    if discovered is None:
        raise OnboardingError("The local Factory setup command is unavailable.")
    return Path(discovered).resolve()


def _terminal_command(command: Sequence[str]) -> list[str]:
    candidates = (
        ("xdg-terminal-exec", ()),
        ("x-terminal-emulator", ("-e",)),
        ("kgx", ("--",)),
        ("gnome-terminal", ("--",)),
        ("konsole", ("-e",)),
        ("xfce4-terminal", ("--execute",)),
        ("xterm", ("-e",)),
    )
    for name, separator in candidates:
        executable = shutil.which(name)
        if executable is not None:
            return [executable, *separator, *command]
    raise OnboardingError(
        "No supported local terminal is available. Open a terminal and run "
        "'bot-factory onboard'; never paste the manager credential into chat."
    )


def _terminal_environment() -> dict[str, str]:
    allowed = {
        "DBUS_SESSION_BUS_ADDRESS",
        "DISPLAY",
        "HOME",
        "LANG",
        "LC_ALL",
        "PATH",
        "SHELL",
        "TERM",
        "USER",
        "WAYLAND_DISPLAY",
        "XAUTHORITY",
        "XDG_CONFIG_HOME",
        "XDG_CURRENT_DESKTOP",
        "XDG_DATA_HOME",
        "XDG_RUNTIME_DIR",
        "XDG_SESSION_TYPE",
        "XDG_STATE_HOME",
    }
    environment = {key: value for key, value in os.environ.items() if key in allowed}
    runtime_value = environment.get("XDG_RUNTIME_DIR")
    if runtime_value:
        runtime = Path(runtime_value)
        bus = runtime / "bus"
        if "DBUS_SESSION_BUS_ADDRESS" not in environment and bus.exists():
            environment["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={bus}"
        if "WAYLAND_DISPLAY" not in environment and runtime.is_dir():
            candidates = sorted(runtime.glob("wayland-[0-9]*"))
            if candidates:
                environment["WAYLAND_DISPLAY"] = candidates[0].name
    if "DISPLAY" not in environment and environment.get("XDG_SESSION_TYPE") == "x11":
        environment["DISPLAY"] = ":0"
    return environment


def launch_setup_terminal() -> OnboardingLaunchResult:
    """Open the secret-bearing wizard in a local terminal, never through MCP input."""
    operator = _operator_executable()
    command = _terminal_command([str(operator), "onboard", "--hold"])
    try:
        subprocess.Popen(  # noqa: S603 - fixed trusted entry point and terminal executable
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            start_new_session=True,
            env=_terminal_environment(),
        )
    except OSError as error:
        raise OnboardingError("The local setup terminal could not be opened safely.") from error
    return OnboardingLaunchResult(
        launched=True,
        status="setup_terminal_opened",
        next_action="Complete setup in the local terminal, then reload MCP tools.",
    )


def install_stable_worker() -> Path:
    """Install the pinned package as a durable uv tool and return its worker path."""
    uv = shutil.which("uv")
    if uv is None:
        raise OnboardingError("uv is required to install the persistent Factory worker.")
    package = f"telegram-managed-bot-factory=={__version__}"
    try:
        subprocess.run([uv, "tool", "install", "--force", package], check=True)  # noqa: S603
        result = subprocess.run(  # noqa: S603
            [uv, "tool", "dir", "--bin"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise OnboardingError("The persistent Factory worker could not be installed.") from error
    manager = (Path(result.stdout.strip()).resolve() / "bot-factory-manager").resolve()
    if not manager.is_file():
        raise OnboardingError("The installed Factory worker command is unavailable.")
    return manager


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
    setup_main(trusted_paths)
    service_start = datetime.now(UTC)
    install_user_service(manager, trusted_paths)
    verify_user_service_active()
    verify_worker_heartbeat(trusted_paths, service_start)
    print("Factory worker is installed, active, and healthy under systemd --user.")
    print("Return to Hermes and reload MCP tools. Never paste credentials into chat.")


def onboard_main(*, hold: bool = False) -> int:
    try:
        run_onboarding(install_stable_worker())
        result = 0
    except (OnboardingError, SetupError, SystemdInstallError) as error:
        print(f"Factory setup did not complete: {error}")
        result = 1
    if hold:
        try:
            input("Press Enter to close this terminal...")
        except EOFError:
            pass
    return result
