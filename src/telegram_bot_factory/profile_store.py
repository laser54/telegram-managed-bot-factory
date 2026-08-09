"""Instance-local profile data stores."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path


class ProfileStoreError(RuntimeError):
    """Safe instance-local data failure."""


class ProfileStore:
    def __init__(self, runtime_dir: Path) -> None:
        self.path = runtime_dir / "profile.sqlite"
        runtime_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        runtime_dir.chmod(0o700)
        if runtime_dir.is_symlink():
            raise ProfileStoreError("Runtime directory is unsafe.")
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    user_id INTEGER PRIMARY KEY,
                    stage TEXT NOT NULL,
                    optional_name TEXT
                );
                CREATE TABLE IF NOT EXISTS leads (
                    lead_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    optional_name TEXT,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS links (
                    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    done INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS inbound_updates (
                    update_id INTEGER PRIMARY KEY,
                    status TEXT NOT NULL CHECK(status IN ('processing', 'complete', 'quarantined')),
                    safe_reason TEXT,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )
        self.path.chmod(0o600)

    def conversation(self, user_id: int) -> tuple[str, str | None] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT stage, optional_name FROM conversations WHERE user_id = ?", (user_id,)
            ).fetchone()
        return None if row is None else (str(row["stage"]), row["optional_name"])

    def set_conversation(self, user_id: int, stage: str, optional_name: str | None) -> None:
        with self._connection() as connection:
            connection.execute(
                """INSERT INTO conversations (user_id, stage, optional_name)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    stage = excluded.stage,
                    optional_name = excluded.optional_name""",
                (user_id, stage, optional_name),
            )

    def clear_conversation(self, user_id: int) -> None:
        with self._connection() as connection:
            connection.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))

    def add_lead(self, user_id: int, optional_name: str | None, message: str) -> int:
        with self._connection() as connection:
            cursor = connection.execute(
                """INSERT INTO leads (user_id, optional_name, message, created_at)
                VALUES (?, ?, ?, ?)""",
                (user_id, optional_name, message, datetime.now(UTC).isoformat()),
            )
            if cursor.lastrowid is None:
                raise ProfileStoreError("Lead could not be stored.")
            return cursor.lastrowid

    def leads(self) -> list[tuple[int, str | None, str]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT lead_id, optional_name, message FROM leads ORDER BY lead_id"
            ).fetchall()
        return [(int(row["lead_id"]), row["optional_name"], str(row["message"])) for row in rows]

    def purge_leads(self) -> int:
        with self._connection() as connection:
            count = int(connection.execute("SELECT count(*) FROM leads").fetchone()[0])
            connection.execute("DELETE FROM leads")
            connection.execute("DELETE FROM conversations")
        return count

    def add_link(self, content: str) -> int:
        with self._connection() as connection:
            cursor = connection.execute(
                "INSERT INTO links (content, created_at) VALUES (?, ?)",
                (content, datetime.now(UTC).isoformat()),
            )
            if cursor.lastrowid is None:
                raise ProfileStoreError("Inbox item could not be stored.")
            return cursor.lastrowid

    def pending_links(self, limit: int = 20) -> list[tuple[int, str]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT item_id, content FROM links WHERE done = 0 ORDER BY item_id LIMIT ?",
                (limit,),
            ).fetchall()
        return [(int(row["item_id"]), str(row["content"])) for row in rows]

    def complete_link(self, item_id: int) -> bool:
        with self._connection() as connection:
            cursor = connection.execute(
                "UPDATE links SET done = 1 WHERE item_id = ? AND done = 0", (item_id,)
            )
        return cursor.rowcount == 1

    def begin_update(self, update_id: int) -> str:
        """Reserve an update before effects; an interrupted reservation is quarantined."""
        now = datetime.now(UTC).isoformat()
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT status FROM inbound_updates WHERE update_id = ?", (update_id,)
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO inbound_updates VALUES (?, 'processing', NULL, ?)",
                    (update_id, now),
                )
                return "process"
            if row["status"] == "processing":
                connection.execute(
                    """UPDATE inbound_updates
                    SET status = 'quarantined', safe_reason = 'ambiguous_effect', updated_at = ?
                    WHERE update_id = ?""",
                    (now, update_id),
                )
                return "quarantine"
            return "skip" if row["status"] == "complete" else "quarantine"

    def complete_update(self, update_id: int) -> None:
        with self._connection() as connection:
            cursor = connection.execute(
                """UPDATE inbound_updates SET status = 'complete', updated_at = ?
                WHERE update_id = ? AND status = 'processing'""",
                (datetime.now(UTC).isoformat(), update_id),
            )
            if cursor.rowcount != 1:
                raise ProfileStoreError("Inbound update acknowledgement is invalid.")

    def update_status(self, update_id: int) -> str | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT status FROM inbound_updates WHERE update_id = ?", (update_id,)
            ).fetchone()
        return None if row is None else str(row["status"])

    def reconciliation_required(self) -> bool:
        """Return true only for a confirmed ambiguous effect, never a live reservation."""
        with self._connection() as connection:
            row = connection.execute(
                "SELECT 1 FROM inbound_updates WHERE status = 'quarantined' LIMIT 1"
            ).fetchone()
        return row is not None

    def update_offset(self) -> int:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT value FROM metadata WHERE key = 'telegram_offset'"
            ).fetchone()
        return 0 if row is None else int(row["value"])

    def advance_update_offset(self, offset: int) -> None:
        with self._connection() as connection:
            connection.execute(
                """INSERT INTO metadata VALUES ('telegram_offset', ?)
                ON CONFLICT(key) DO UPDATE SET value = max(CAST(value AS INTEGER), ?)""",
                (str(offset), offset),
            )

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
