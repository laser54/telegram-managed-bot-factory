"""Linux systemd user service installation."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from telegram_bot_factory.paths import FactoryPaths


class SystemdInstallError(RuntimeError):
    """Safe service installation failure."""


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
PrivateDevices=true
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
        raise SystemdInstallError("The v0.1 worker service supports Linux only.")
    destination_dir = unit_dir or (Path.home() / ".config" / "systemd" / "user")
    destination_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    unit_path = destination_dir / "bot-factory-manager.service"
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
