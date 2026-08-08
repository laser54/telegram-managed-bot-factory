from pathlib import Path

from scripts.scan_release import scan_path
from tests.sentinels import token_shaped_sentinel


def test_release_scanner_finds_token_shapes_without_printing_them(tmp_path: Path) -> None:
    safe = tmp_path / "safe.txt"
    unsafe = tmp_path / "unsafe.txt"
    safe.write_text("ordinary release metadata", encoding="utf-8")
    unsafe.write_text(token_shaped_sentinel("SCAN_SENTINEL"), encoding="utf-8")

    assert scan_path(safe) == []
    assert scan_path(unsafe) == [str(unsafe)]
