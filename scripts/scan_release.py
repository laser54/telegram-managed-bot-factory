"""Fail closed when a Telegram-token-shaped value appears in release material."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import tarfile
import zipfile
from collections.abc import Iterable
from pathlib import Path

TOKEN_PATTERN = re.compile(rb"(?<![0-9])[0-9]{8,12}:[A-Za-z0-9_-]{20,}(?![A-Za-z0-9_-])")


def archive_members(path: Path) -> Iterable[tuple[str, bytes]]:
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            for member in archive.infolist():
                if not member.is_dir():
                    yield member.filename, archive.read(member)
    elif tarfile.is_tarfile(path):
        with tarfile.open(path) as archive:
            for member in archive.getmembers():
                if member.isfile():
                    extracted = archive.extractfile(member)
                    if extracted is not None:
                        yield member.name, extracted.read()


def scan_path(path: Path) -> list[str]:
    failures: list[str] = []
    candidates = [path] if path.is_file() else [item for item in path.rglob("*") if item.is_file()]
    for candidate in candidates:
        if any(part in {".git", ".venv", "__pycache__"} for part in candidate.parts):
            continue
        try:
            members = list(archive_members(candidate))
            blobs = members or [(candidate.name, candidate.read_bytes())]
        except (OSError, tarfile.TarError, zipfile.BadZipFile):
            failures.append(str(candidate))
            continue
        if any(TOKEN_PATTERN.search(blob) for _, blob in blobs):
            failures.append(str(candidate))
    return failures


def scan_git_history(repository: Path) -> bool:
    git = shutil.which("git")
    if git is None:
        raise RuntimeError("Git is required for history scanning.")
    result = subprocess.run(  # noqa: S603 - executable is resolved locally, no shell
        [git, "log", "-p", "--all", "--no-ext-diff", "--binary"],
        cwd=repository,
        check=True,
        capture_output=True,
    )
    return TOKEN_PATTERN.search(result.stdout) is None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", type=Path, default=[Path("src"), Path("dist")])
    parser.add_argument("--git-history", action="store_true")
    arguments = parser.parse_args()
    failures = [failure for path in arguments.paths if path.exists() for failure in scan_path(path)]
    if arguments.git_history and not scan_git_history(Path.cwd()):
        failures.append("Git history")
    if failures:
        print("Potential credential material found in: " + ", ".join(failures))
        return 1
    print("Credential-shape scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
