"""SQLite-backed non-secret Factory state."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from pydantic import TypeAdapter

from telegram_bot_factory.models import (
    FactoryRequest,
    InstanceRecord,
    ProfileConfig,
    ProfileName,
    RequestState,
)

PROFILE_CONFIG_ADAPTER: TypeAdapter[ProfileConfig] = TypeAdapter(ProfileConfig)

ALLOWED_TRANSITIONS: dict[RequestState, frozenset[RequestState]] = {
    RequestState.PENDING_CONFIRMATION: frozenset(
        {
            RequestState.MANAGED_UPDATE_RECEIVED,
            RequestState.FAILED,
            RequestState.RECONCILIATION_REQUIRED,
        }
    ),
    RequestState.MANAGED_UPDATE_RECEIVED: frozenset(
        {RequestState.TOKEN_RECEIVED, RequestState.FAILED, RequestState.RECONCILIATION_REQUIRED}
    ),
    RequestState.TOKEN_RECEIVED: frozenset(
        {
            RequestState.INSTANCE_MATERIALIZED,
            RequestState.FAILED,
            RequestState.RECONCILIATION_REQUIRED,
        }
    ),
    RequestState.INSTANCE_MATERIALIZED: frozenset(
        {RequestState.ACTIVE, RequestState.FAILED, RequestState.RECONCILIATION_REQUIRED}
    ),
    RequestState.ACTIVE: frozenset({RequestState.STOPPED}),
    RequestState.STOPPED: frozenset({RequestState.ACTIVE, RequestState.RETIRED}),
    RequestState.FAILED: frozenset(),
    RequestState.RECONCILIATION_REQUIRED: frozenset(),
    RequestState.RETIRED: frozenset(),
}


class StateError(RuntimeError):
    """Safe durable-state failure."""


class FactoryState:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def initialize(self) -> None:
        self.database_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.database_path.parent.chmod(0o700)
        with self._connection() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode = WAL;
                PRAGMA foreign_keys = ON;
                CREATE TABLE IF NOT EXISTS requests (
                    request_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    username TEXT NOT NULL UNIQUE,
                    slug TEXT NOT NULL UNIQUE,
                    profile TEXT NOT NULL,
                    profile_config TEXT NOT NULL,
                    owner_telegram_id INTEGER NOT NULL,
                    purpose TEXT,
                    notify_owner INTEGER NOT NULL,
                    state TEXT NOT NULL,
                    safe_reason TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS lifecycle_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL REFERENCES requests(request_id),
                    from_state TEXT,
                    to_state TEXT NOT NULL,
                    safe_reason TEXT,
                    occurred_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS processed_updates (
                    update_id INTEGER PRIMARY KEY,
                    request_id TEXT NOT NULL REFERENCES requests(request_id),
                    processed_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS reconciliation_events (
                    update_id INTEGER PRIMARY KEY,
                    safe_reason TEXT NOT NULL,
                    occurred_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS instances (
                    slug TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL UNIQUE REFERENCES requests(request_id),
                    username TEXT NOT NULL UNIQUE,
                    profile TEXT NOT NULL,
                    owner_telegram_id INTEGER NOT NULL,
                    state TEXT NOT NULL,
                    health TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )
        self.database_path.chmod(0o600)

    def create_request(self, request: FactoryRequest) -> None:
        self.initialize()
        values = self._request_values(request)
        try:
            with self._connection() as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    """
                    INSERT INTO requests (
                        request_id, display_name, username, slug, profile, profile_config,
                        owner_telegram_id, purpose, notify_owner, state, safe_reason,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
                connection.execute(
                    """INSERT INTO lifecycle_events
                    (request_id, from_state, to_state, safe_reason, occurred_at)
                    VALUES (?, NULL, ?, NULL, ?)""",
                    (str(request.request_id), request.state.value, request.created_at.isoformat()),
                )
        except sqlite3.IntegrityError as error:
            raise StateError("Request username, slug, or identifier already exists.") from error

    def get_request(self, request_id: UUID) -> FactoryRequest | None:
        self.initialize()
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM requests WHERE request_id = ?", (str(request_id),)
            ).fetchone()
        return None if row is None else self._request_from_row(row)

    def list_requests(self, state: RequestState | None = None) -> list[FactoryRequest]:
        self.initialize()
        query = "SELECT * FROM requests"
        parameters: tuple[str, ...] = ()
        if state is not None:
            query += " WHERE state = ?"
            parameters = (state.value,)
        query += " ORDER BY created_at, request_id"
        with self._connection() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [self._request_from_row(row) for row in rows]

    def find_pending(self, username: str, owner_telegram_id: int) -> FactoryRequest | None:
        self.initialize()
        with self._connection() as connection:
            row = connection.execute(
                """SELECT * FROM requests
                WHERE lower(username) = lower(?)
                  AND owner_telegram_id = ?
                  AND state = ?""",
                (username, owner_telegram_id, RequestState.PENDING_CONFIRMATION.value),
            ).fetchone()
        return None if row is None else self._request_from_row(row)

    def pending_for_owner(self, owner_telegram_id: int) -> list[FactoryRequest]:
        self.initialize()
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT * FROM requests
                WHERE owner_telegram_id = ? AND state = ?
                ORDER BY created_at, request_id""",
                (owner_telegram_id, RequestState.PENDING_CONFIRMATION.value),
            ).fetchall()
        return [self._request_from_row(row) for row in rows]

    def transition(
        self, request_id: UUID, target: RequestState, safe_reason: str | None = None
    ) -> FactoryRequest:
        if safe_reason is not None and len(safe_reason) > 100:
            raise StateError("Safe reason is too long.")
        self.initialize()
        now = datetime.now(UTC).isoformat()
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM requests WHERE request_id = ?", (str(request_id),)
            ).fetchone()
            if row is None:
                raise StateError("Request does not exist.")
            current = RequestState(row["state"])
            if current == target:
                return self._request_from_row(row)
            if target not in ALLOWED_TRANSITIONS[current]:
                raise StateError("Lifecycle transition is not allowed.")
            connection.execute(
                """UPDATE requests
                SET state = ?, safe_reason = ?, updated_at = ?
                WHERE request_id = ?""",
                (target.value, safe_reason, now, str(request_id)),
            )
            connection.execute(
                """INSERT INTO lifecycle_events
                (request_id, from_state, to_state, safe_reason, occurred_at)
                VALUES (?, ?, ?, ?, ?)""",
                (str(request_id), current.value, target.value, safe_reason, now),
            )
            updated = connection.execute(
                "SELECT * FROM requests WHERE request_id = ?", (str(request_id),)
            ).fetchone()
        if updated is None:  # pragma: no cover - protected by transaction
            raise StateError("Request disappeared during transition.")
        return self._request_from_row(updated)

    def mark_update_processed(self, update_id: int, request_id: UUID) -> bool:
        if update_id < 0:
            raise StateError("Update identifier is invalid.")
        self.initialize()
        try:
            with self._connection() as connection:
                connection.execute(
                    """INSERT INTO processed_updates (update_id, request_id, processed_at)
                    VALUES (?, ?, ?)""",
                    (update_id, str(request_id), datetime.now(UTC).isoformat()),
                )
        except sqlite3.IntegrityError:
            return False
        return True

    def polling_offset(self) -> int:
        self.initialize()
        with self._connection() as connection:
            row = connection.execute(
                "SELECT value FROM metadata WHERE key = 'polling_offset'"
            ).fetchone()
        return 0 if row is None else int(row["value"])

    def advance_polling_offset(self, offset: int) -> int:
        if offset < 0:
            raise StateError("Polling offset is invalid.")
        self.initialize()
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current = connection.execute(
                "SELECT value FROM metadata WHERE key = 'polling_offset'"
            ).fetchone()
            current_value = 0 if current is None else int(current["value"])
            value = max(current_value, offset)
            connection.execute(
                """INSERT INTO metadata (key, value) VALUES ('polling_offset', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
                (str(value),),
            )
        return value

    def record_reconciliation_event(self, update_id: int, safe_reason: str) -> bool:
        if update_id < 0 or not safe_reason or len(safe_reason) > 100:
            raise StateError("Reconciliation event is invalid.")
        self.initialize()
        try:
            with self._connection() as connection:
                connection.execute(
                    """INSERT INTO reconciliation_events
                    (update_id, safe_reason, occurred_at) VALUES (?, ?, ?)""",
                    (update_id, safe_reason, datetime.now(UTC).isoformat()),
                )
        except sqlite3.IntegrityError:
            return False
        return True

    def reconciliation_event_count(self) -> int:
        self.initialize()
        with self._connection() as connection:
            row = connection.execute(
                "SELECT count(*) AS total FROM reconciliation_events"
            ).fetchone()
        return 0 if row is None else int(row["total"])

    def upsert_instance(self, instance: InstanceRecord) -> None:
        self.initialize()
        try:
            with self._connection() as connection:
                connection.execute(
                    """
                    INSERT INTO instances (
                        slug, request_id, username, profile, owner_telegram_id,
                        state, health, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(slug) DO UPDATE SET
                        state = excluded.state,
                        health = excluded.health,
                        updated_at = excluded.updated_at
                    """,
                    (
                        instance.slug,
                        str(instance.request_id),
                        instance.username,
                        instance.profile.value,
                        instance.owner_telegram_id,
                        instance.state.value,
                        instance.health,
                        instance.created_at.isoformat(),
                        instance.updated_at.isoformat(),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise StateError("Instance conflicts with existing state.") from error

    def list_instances(self) -> list[InstanceRecord]:
        self.initialize()
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM instances ORDER BY created_at, slug"
            ).fetchall()
        return [self._instance_from_row(row) for row in rows]

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _request_values(request: FactoryRequest) -> tuple[object, ...]:
        return (
            str(request.request_id),
            request.display_name,
            request.username,
            request.slug,
            request.profile.value,
            request.profile_config.model_dump_json(),
            request.owner_telegram_id,
            request.purpose,
            int(request.notify_owner),
            request.state.value,
            request.safe_reason,
            request.created_at.isoformat(),
            request.updated_at.isoformat(),
        )

    @staticmethod
    def _request_from_row(row: sqlite3.Row) -> FactoryRequest:
        return FactoryRequest(
            request_id=UUID(row["request_id"]),
            display_name=row["display_name"],
            username=row["username"],
            slug=row["slug"],
            profile=ProfileName(row["profile"]),
            profile_config=PROFILE_CONFIG_ADAPTER.validate_json(row["profile_config"], strict=True),
            owner_telegram_id=row["owner_telegram_id"],
            purpose=row["purpose"],
            notify_owner=bool(row["notify_owner"]),
            state=RequestState(row["state"]),
            safe_reason=row["safe_reason"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _instance_from_row(row: sqlite3.Row) -> InstanceRecord:
        return InstanceRecord(
            slug=row["slug"],
            request_id=UUID(row["request_id"]),
            username=row["username"],
            profile=ProfileName(row["profile"]),
            owner_telegram_id=row["owner_telegram_id"],
            state=RequestState(row["state"]),
            health=row["health"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
