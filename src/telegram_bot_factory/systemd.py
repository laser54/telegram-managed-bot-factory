"""Linux systemd user service installation."""

from __future__ import annotations

import getpass
import os
import shutil
import subprocess
from pathlib import Path

from telegram_bot_factory.paths import FactoryPaths


class SystemdInstallError(RuntimeError):
    """Safe service installation failure."""


SERVICE_NAME = "bot-factory-manager.service"


def _required_systemctl() -> str:
    systemctl = shutil.which("systemctl")
    if systemctl is None:
        raise SystemdInstallError("systemctl is unavailable.")
    return systemctl


def ensure_user_systemd_available() -> None:
    """Fail before secret setup when the required user service manager is unavailable."""
    systemctl = _required_systemctl()
    try:
        subprocess.run(  # noqa: S603 - resolved trusted systemctl executable
            [systemctl, "--user", "show-environment"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise SystemdInstallError(
            "systemd --user is unavailable. Run 'systemctl --user show-environment' "
            "in this local terminal, enable a user systemd session, and retry. No worker "
            "was started."
        ) from error


def ensure_user_lingering() -> None:
    """Keep the user manager alive after the interactive SSH session exits."""
    loginctl = shutil.which("loginctl")
    username = getpass.getuser()
    if loginctl is None:
        raise SystemdInstallError(
            "loginctl is unavailable, so Factory cannot ensure the worker survives logout."
        )
    try:
        current = subprocess.run(  # noqa: S603 - resolved trusted loginctl executable
            [loginctl, "show-user", username, "-p", "Linger", "--value"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if current != "yes":
            subprocess.run(  # noqa: S603 - resolved trusted loginctl executable
                [loginctl, "enable-linger", username], check=True
            )
            verified = subprocess.run(  # noqa: S603 - resolved trusted loginctl executable
                [loginctl, "show-user", username, "-p", "Linger", "--value"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            if verified != "yes":
                raise SystemdInstallError(
                    "systemd lingering is not enabled, so Factory cannot survive logout."
                )
    except (OSError, subprocess.CalledProcessError) as error:
        raise SystemdInstallError(
            "Could not enable systemd lingering for this user, so Factory cannot survive logout."
        ) from error


def verify_user_service_active() -> None:
    """Require the persistent worker to be active and enabled before onboarding succeeds."""
    systemctl = _required_systemctl()
    try:
        subprocess.run(  # noqa: S603 - resolved trusted systemctl executable
            [systemctl, "--user", "is-active", "--quiet", SERVICE_NAME],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(  # noqa: S603 - resolved trusted systemctl executable
            [systemctl, "--user", "is-enabled", "--quiet", SERVICE_NAME],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise SystemdInstallError(
            "The Factory worker service is not active and enabled. Inspect it locally with "
            "'systemctl --user status bot-factory-manager.service'."
        ) from error


def user_service_is_ready() -> bool:
    """Return whether the mandatory persistent worker unit is active and enabled."""
    try:
        verify_user_service_active()
    except SystemdInstallError:
        return False
    return True


def render_user_unit(manager_executable: Path, paths: FactoryPaths) -> str:
    if not manager_executable.is_absolute():
        raise SystemdInstallError("Manager executable must be absolute.")
    manager_value = _unit_quote(manager_executable)
    writable = " ".join(
        _unit_quote(path) for path in (paths.config_dir, paths.data_dir, paths.state_dir)
    )
    return f"""[Unit]
Description=Telegram Managed Bot Factory worker
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart={manager_value} run
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths={writable}
RestrictSUIDSGID=true
LockPersonality=true

[Install]
WantedBy=default.target
"""


def _unit_quote(path: Path) -> str:
    value = str(path)
    if "\n" in value or "\r" in value or "\x00" in value:
        raise SystemdInstallError("Service path contains unsafe characters.")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def install_user_service(
    manager_executable: Path,
    paths: FactoryPaths,
    unit_dir: Path | None = None,
) -> Path:
    if os.name != "posix":
        raise SystemdInstallError("The Factory worker service supports Linux only.")
    destination_dir = unit_dir or (Path.home() / ".config" / "systemd" / "user")
    destination_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    unit_path = destination_dir / SERVICE_NAME
    temporary = destination_dir / ".bot-factory-manager.pending"
    temporary.write_text(render_user_unit(manager_executable, paths), encoding="utf-8")
    temporary.chmod(0o600)
    os.replace(temporary, unit_path)
    systemctl = shutil.which("systemctl")
    if systemctl is None:
        raise SystemdInstallError("systemctl is unavailable.")
    try:
        subprocess.run(  # noqa: S603 - resolved trusted systemctl executable
            [systemctl, "--user", "daemon-reload"], check=True
        )
        subprocess.run(  # noqa: S603 - resolved trusted systemctl executable
            [systemctl, "--user", "enable", "--now", unit_path.name], check=True
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise SystemdInstallError("systemd user service could not be enabled.") from error
    return unit_path
