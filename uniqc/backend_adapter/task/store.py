"""SQLite-backed task storage for UnifiedQuantum.

This module is the single source of truth for task persistence. Both
:mod:`uniqc.backend_adapter.task_manager` and :mod:`uniqc.backend_adapter.task.persistence` delegate to
:class:`TaskStore`; there is no JSON/JSONL fallback path.

Storage layout::

    ~/.uniqc/cache/
        tasks.sqlite          # single database file

Schema versioning (best practices)
----------------------------------

The database uses SQLite's built-in metadata slots in the file header
rather than a custom bookkeeping table:

- ``PRAGMA application_id`` holds :data:`APPLICATION_ID` (the 4 bytes
  ``"UNIC"``). On open we refuse to touch a file whose ``application_id``
  is set to something else; a zero value means a fresh DB we can stamp.
- ``PRAGMA user_version`` holds the integer schema version. It is bumped
  by each migration and used to decide what else to run.

:data:`MIGRATIONS` is an ordered list of ``(target_version, migrate_fn)``
tuples. To evolve the schema:

1. Append a new tuple ``(N, _apply_vN)`` where ``N = CURRENT_SCHEMA_VERSION + 1``.
2. Bump :data:`CURRENT_SCHEMA_VERSION` to ``N``.
3. Implement ``_apply_vN(conn)`` (DDL or DML on the given connection).

On open, :class:`TaskStore` iterates the list and runs each outstanding
migration in its own transaction; ``user_version`` is stamped as part of
the same transaction so a crashed migration rolls back the version bump
too.
"""

from __future__ import annotations

__all__ = [
    "APPLICATION_ID",
    "CURRENT_SCHEMA_VERSION",
    "DEFAULT_CACHE_DIR",
    "MIGRATIONS",
    "TERMINAL_STATUSES",
    "TaskInfo",
    "TaskStatus",
    "TaskStore",
]

import json
import sqlite3
import tempfile
import threading
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterator

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------

DEFAULT_CACHE_DIR: Path = Path.home() / ".uniqc" / "cache"
DB_FILENAME: str = "tasks.sqlite"

# Four ASCII bytes 'UNIC' (short for uniqc -- can't fit all five letters in
# 32 bits), stored in the SQLite header so we can tell "this is our cache"
# from "this is somebody else's random tasks.sqlite".
APPLICATION_ID: int = 0x554E4943  # b"UNIC"

CURRENT_SCHEMA_VERSION: int = 2

TERMINAL_STATUSES: tuple[str, ...] = ("success", "failed", "cancelled")


# ---------------------------------------------------------------------------
# Task types
# ---------------------------------------------------------------------------

class TaskStatus(str, Enum):
    """Enumeration of task statuses."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskInfo:
    """Information about a submitted task.

    Attributes:
        task_id: Unique identifier for the task.
        backend: The backend where the task was submitted.
        status: Current status of the task.
        result: Task result (if completed).
        shots: Number of shots requested.
        submit_time: ISO format timestamp of submission.
        update_time: ISO format timestamp of last status update.
        metadata: Additional metadata about the task.
        error_message: When ``status == FAILED`` (or for any non-success
            terminal state) this carries a human-readable explanation —
            e.g. the dummy adapter's stderr or the cloud platform's
            error string. ``None`` while the task is still running or on
            success.
        archived_at: Timestamp when the task was archived; ``None`` if
            still in the live ``tasks`` table.
    """

    task_id: str
    backend: str
    status: str = TaskStatus.PENDING
    result: dict | None = None
    shots: int = 1000
    submit_time: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    update_time: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict = field(default_factory=dict)
    error_message: str | None = None
    archived_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskInfo":
        """Create from dictionary."""
        # Tolerate older snapshots that didn't carry ``error_message``.
        if "error_message" not in data:
            data = {**data, "error_message": None}
        return cls(**data)


# ---------------------------------------------------------------------------
# Schema DDL + migrations
# ---------------------------------------------------------------------------

_TASKS_DDL = """
CREATE TABLE IF NOT EXISTS tasks (
    task_id       TEXT PRIMARY KEY,
    backend       TEXT NOT NULL,
    status        TEXT NOT NULL,
    shots         INTEGER NOT NULL DEFAULT 0,
    submit_time   TEXT NOT NULL,
    update_time   TEXT NOT NULL,
    result_json   TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
)
"""

_INDEX_DDL: tuple[str, ...] = (
    "CREATE INDEX IF NOT EXISTS tasks_backend_idx     ON tasks(backend)",
    "CREATE INDEX IF NOT EXISTS tasks_status_idx      ON tasks(status)",
    "CREATE INDEX IF NOT EXISTS tasks_submit_time_idx ON tasks(submit_time)",
)


def _apply_v1(conn: sqlite3.Connection) -> None:
    """Initial schema: ``tasks`` table + indices."""
    conn.execute(_TASKS_DDL)
    for ddl in _INDEX_DDL:
        conn.execute(ddl)


_ARCHIVED_TASKS_DDL = """
CREATE TABLE IF NOT EXISTS archived_tasks (
    task_id       TEXT PRIMARY KEY,
    backend       TEXT NOT NULL,
    status        TEXT NOT NULL,
    shots         INTEGER NOT NULL DEFAULT 0,
    submit_time   TEXT NOT NULL,
    update_time   TEXT NOT NULL,
    result_json   TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    archived_at   TEXT NOT NULL
)
"""


def _apply_v2(conn: sqlite3.Connection) -> None:
    """v2: add ``archived_tasks`` table for task archiving."""
    conn.execute(_ARCHIVED_TASKS_DDL)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS archived_backend_idx ON archived_tasks(backend)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS archived_status_idx  ON archived_tasks(status)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS archived_submit_time_idx ON archived_tasks(submit_time)"
    )


def _apply_v3(conn: sqlite3.Connection) -> None:
    """v3: add ``error_message`` column to ``tasks`` and ``archived_tasks``."""
    for table in ("tasks", "archived_tasks"):
        # Use try/except: ALTER TABLE ADD COLUMN is not idempotent across
        # SQLite versions and we want migrations to be safe to re-apply.
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN error_message TEXT")
        except sqlite3.OperationalError as e:  # noqa: PERF203
            if "duplicate column" not in str(e).lower():
                raise


MigrateFn = Callable[[sqlite3.Connection], None]

# Ordered list of ``(target_version, migrate_fn)``. Append future migrations
# here; never reorder or delete past entries.
MIGRATIONS: list[tuple[int, MigrateFn]] = [
    (1, _apply_v1),
    (2, _apply_v2),
    (3, _apply_v3),
]


# ---------------------------------------------------------------------------
# Header metadata + status helpers
# ---------------------------------------------------------------------------

def _normalize_status(status: Any) -> str:
    """Return the canonical string value for a status.

    Accepts either a plain string or a ``TaskStatus`` enum member. The
    enum inherits from ``str`` but its ``__str__`` returns the repr form
    (``"TaskStatus.RUNNING"``), which is not what we want in the DB.
    ``status.value`` yields the literal.
    """
    if isinstance(status, TaskStatus):
        return status.value
    return str(status)


def _get_user_version(conn: sqlite3.Connection) -> int:
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


def _set_user_version(conn: sqlite3.Connection, version: int) -> None:
    # PRAGMA values cannot be parameter-bound, so interpolate an int.
    conn.execute(f"PRAGMA user_version = {int(version)}")


def _get_application_id(conn: sqlite3.Connection) -> int:
    return int(conn.execute("PRAGMA application_id").fetchone()[0])


def _set_application_id(conn: sqlite3.Connection, app_id: int) -> None:
    conn.execute(f"PRAGMA application_id = {int(app_id)}")


# ---------------------------------------------------------------------------
# Row <-> TaskInfo
# ---------------------------------------------------------------------------

def _row_to_info(row: sqlite3.Row) -> TaskInfo:
    result = json.loads(row["result_json"]) if row["result_json"] else None
    metadata = json.loads(row["metadata_json"]) if row["metadata_json"] else {}
    # archived_at only exists in archived_tasks, not in tasks
    archived_at = row["archived_at"] if "archived_at" in row.keys() else None
    error_message = row["error_message"] if "error_message" in row.keys() else None
    return TaskInfo(
        task_id=row["task_id"],
        backend=row["backend"],
        status=row["status"],
        shots=int(row["shots"]),
        submit_time=row["submit_time"],
        update_time=row["update_time"],
        result=result,
        metadata=metadata,
        error_message=error_message,
        archived_at=archived_at,
    )


# ---------------------------------------------------------------------------
# TaskStore
# ---------------------------------------------------------------------------

class TaskStore:
    """SQLite-backed storage for task records.

    ``TaskStore`` is safe to construct multiple times against the same
    cache directory; all operations use short-lived connections guarded
    by a per-instance lock.

    Args:
        cache_dir: Directory that holds ``tasks.sqlite``. Defaults to
            ``~/.uniqc/cache/``. The directory is created if missing.
    """

    def __init__(self, cache_dir: Path | str | None = None) -> None:
        self.cache_dir: Path = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path: Path = self.cache_dir / DB_FILENAME
        self._lock = threading.RLock()
        try:
            self._init_schema()
        except sqlite3.OperationalError:
            if cache_dir is not None:
                raise
            self.cache_dir = Path(tempfile.gettempdir()) / "uniqc" / "cache"
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = self.cache_dir / DB_FILENAME
            self._init_schema()

    # -- connection / transaction helpers -----------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        # WAL gives us concurrent readers and resilience across crashes.
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Connection]:
        """Yield a connection inside a committed transaction."""
        with self._lock:
            conn = self._connect()
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()

    # -- schema init + migrations -------------------------------------------

    def _init_schema(self) -> None:
        # Open one connection for the whole init dance. PRAGMAs on journal
        # mode etc. need to be outside a transaction.
        with self._lock:
            conn = self._connect()
            try:
                self._stamp_or_check_application_id(conn)

                current = _get_user_version(conn)
                for target, migrate_fn in MIGRATIONS:
                    if current < target:
                        with conn:  # BEGIN / COMMIT (or ROLLBACK on error)
                            migrate_fn(conn)
                            _set_user_version(conn, target)
                        current = target
            finally:
                conn.close()

    @staticmethod
    def _stamp_or_check_application_id(conn: sqlite3.Connection) -> None:
        """Stamp ``APPLICATION_ID`` on a fresh DB; refuse foreign ones."""
        existing = _get_application_id(conn)
        if existing == 0:
            _set_application_id(conn, APPLICATION_ID)
        elif existing != APPLICATION_ID:
            raise RuntimeError(
                "SQLite file has application_id="
                f"0x{existing:08x}, expected 0x{APPLICATION_ID:08x} (UNIC). "
                "Refusing to operate on an unknown database."
            )

    # -- CRUD ---------------------------------------------------------------

    def save(self, task_info: TaskInfo) -> None:
        """Insert or update a task record (by ``task_id``).

        Also stamps ``task_info.update_time`` with the current timestamp so
        callers see the same value that was persisted.
        """
        now = datetime.now(timezone.utc).isoformat()
        task_info.update_time = now
        result_json = json.dumps(task_info.result) if task_info.result is not None else None
        metadata_json = json.dumps(task_info.metadata or {}, ensure_ascii=False)
        # ``TaskStatus`` inherits from ``str`` so passing it through binds the
        # underlying enum value (e.g. "running"); calling ``str()`` instead
        # would store the ``"TaskStatus.RUNNING"`` repr, which is wrong.
        params = {
            "task_id": task_info.task_id,
            "backend": task_info.backend,
            "status": _normalize_status(task_info.status),
            "shots": int(task_info.shots),
            "submit_time": task_info.submit_time,
            "update_time": now,
            "result_json": result_json,
            "metadata_json": metadata_json,
            "error_message": task_info.error_message,
        }
        with self._tx() as conn:
            conn.execute(
                """
                INSERT INTO tasks
                    (task_id, backend, status, shots, submit_time, update_time,
                     result_json, metadata_json, error_message)
                VALUES
                    (:task_id, :backend, :status, :shots, :submit_time, :update_time,
                     :result_json, :metadata_json, :error_message)
                ON CONFLICT(task_id) DO UPDATE SET
                    backend       = excluded.backend,
                    status        = excluded.status,
                    shots         = excluded.shots,
                    update_time   = excluded.update_time,
                    result_json   = excluded.result_json,
                    metadata_json = excluded.metadata_json,
                    error_message = excluded.error_message
                """,
                params,
            )

    def get(self, task_id: str) -> TaskInfo | None:
        """Return a task by id, or ``None`` if missing."""
        with self._tx() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
        return _row_to_info(row) if row is not None else None

    def list(
        self,
        *,
        status: str | None = None,
        backend: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[TaskInfo]:
        """List tasks, newest first (by ``submit_time``)."""
        conditions: list[str] = []
        params: list[Any] = []
        if status is not None:
            conditions.append("status = ?")
            params.append(_normalize_status(status))
        if backend is not None:
            conditions.append("backend = ?")
            params.append(backend)
        sql = "SELECT * FROM tasks"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY submit_time DESC, rowid DESC"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(int(limit))
        if offset is not None:
            if limit is None:
                sql += " LIMIT -1"
            sql += " OFFSET ?"
            params.append(int(offset))
        with self._tx() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_row_to_info(row) for row in rows]

    def count(self, *, status: str | None = None, backend: str | None = None) -> int:
        conditions: list[str] = []
        params: list[Any] = []
        if status is not None:
            conditions.append("status = ?")
            params.append(_normalize_status(status))
        if backend is not None:
            conditions.append("backend = ?")
            params.append(backend)
        sql = "SELECT COUNT(*) AS c FROM tasks"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        with self._tx() as conn:
            row = conn.execute(sql, params).fetchone()
        return int(row["c"]) if row is not None else 0

    def delete(self, task_id: str) -> bool:
        """Remove a single task. Returns ``True`` if it existed."""
        with self._tx() as conn:
            cur = conn.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
            return cur.rowcount > 0

    def clear_completed(
        self, terminal_statuses: tuple[str, ...] = TERMINAL_STATUSES
    ) -> int:
        """Delete tasks whose status is in ``terminal_statuses``."""
        placeholders = ",".join("?" for _ in terminal_statuses)
        with self._tx() as conn:
            cur = conn.execute(
                f"DELETE FROM tasks WHERE status IN ({placeholders})",
                [_normalize_status(s) for s in terminal_statuses],
            )
            return cur.rowcount

    def clear_all(self) -> None:
        """Delete the on-disk SQLite file (and its WAL/SHM siblings).

        Matches the pre-SQLite ``clear_cache`` semantics: the cache file
        disappears. A subsequent operation re-initialises the schema.
        """
        with self._lock:
            for path in (
                self.db_path,
                self.db_path.with_name(self.db_path.name + "-wal"),
                self.db_path.with_name(self.db_path.name + "-shm"),
            ):
                if path.exists():
                    try:
                        path.unlink()
                    except OSError:
                        pass
