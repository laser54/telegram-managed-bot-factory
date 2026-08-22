"""One-line user installer for Hermes and the Linux worker."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from telegram_bot_factory import __version__
from telegram_bot_factory.onboarding import OnboardingError, run_onboarding
from telegram_bot_factory.paths import FactoryPaths
from telegram_bot_factory.setup import SetupError
from telegram_bot_factory.systemd import SystemdInstallError


class InstallError(RuntimeError):
    """Safe installation failure."""


def _hermes_test_verified(output: str) -> bool:
    return "Connection failed" not in output and "Tools discovered: 9" in output


def _required_command(name: str) -> str:
    value = shutil.which(name)
    if value is None:
        raise InstallError(f"Required command {name!r} is unavailable.")
    return value


def _register_hermes(hermes: str, mcp_command: Path) -> None:
    """Register through Hermes' current terminal so confirmations remain visible."""
    subprocess.run(  # noqa: S603
        [hermes, "mcp", "add", "bot-factory", "--command", str(mcp_command)],
        check=True,
    )


def install_for_hermes(paths: FactoryPaths | None = None) -> None:
    if os.name != "posix":
        raise InstallError("Factory installation supports Linux only.")
    uv = _required_command("uv")
    hermes = _required_command("hermes")
    package = f"telegram-managed-bot-factory=={__version__}"
    try:
        subprocess.run([uv, "tool", "install", "--force", package], check=True)  # noqa: S603
        bin_result = subprocess.run(  # noqa: S603
            [uv, "tool", "dir", "--bin"],
            check=True,
            capture_output=True,
            text=True,
        )
        bin_dir = Path(bin_result.stdout.strip()).resolve()
        manager = bin_dir / "bot-factory-manager"
        operator = bin_dir / "bot-factory"
        mcp_command = bin_dir / "bot-factory-mcp"
        for executable in (manager, operator, mcp_command):
            if not executable.is_file():
                raise InstallError("Installed Factory entry points are unavailable.")
        trusted_paths = paths or FactoryPaths.discover()
        run_onboarding(manager, trusted_paths)
        _register_hermes(hermes, mcp_command)
        test_result = subprocess.run(  # noqa: S603
            [hermes, "mcp", "test", "bot-factory"],
            check=True,
            capture_output=True,
            text=True,
        )
        test_output = test_result.stdout + test_result.stderr
        if not _hermes_test_verified(test_output):
            raise InstallError("Hermes could not verify the nine-tool Factory catalog.")
        print("Hermes registration verified with nine Factory tools.")
    except (OnboardingError, SetupError, SystemdInstallError) as error:
        raise InstallError(str(error)) from error
    except (OSError, subprocess.CalledProcessError) as error:
        raise InstallError("Factory installation did not complete safely.") from error
