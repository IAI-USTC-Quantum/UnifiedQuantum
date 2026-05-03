"""Archive store — moves tasks in/out of the ``archived_tasks`` table.

The archive lives in the same ``tasks.sqlite`` file as the main task store.
This module provides an ``ArchiveStore`` class that mirrors ``TaskStore``'s
interface but operates on the ``archived_tasks`` table.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from uniqc.backend_adapter.task.store import TaskInfo, TaskStore


class ArchiveStore:
    """Persistent archive for completed / failed tasks.

    Tasks are moved atomically from ``tasks`` → ``archived_tasks`` so that
    the hot-path query on ``tasks`` stays fast even when many historical
    tasks have accumulated.
    """

    def __init__(self) -> None:
        self._store = TaskStore()

    def archive_task(self, task_id: str) -> bool:
        """Move a task from ``tasks`` to ``archived_tasks``.

        Returns ``True`` if the task existed and was moved.
        """
        with self._store._tx() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
            if not row:
                return False
            cols = list(row.keys())
            values = [row[c] for c in cols]
            archived_at = datetime.now(timezone.utc).isoformat()
            conn.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
            placeholders = ",".join("?" * len(cols))
            conn.execute(
                f"INSERT INTO archived_tasks ({','.join(cols)}, archived_at) "
                f"VALUES ({placeholders}, ?)",
                values + [archived_at],
            )
        return True

    def restore_task(self, task_id: str) -> bool:
        """Move a task from ``archived_tasks`` back to ``tasks``.

        Returns ``True`` if the task existed and was restored.
        """
        with self._store._tx() as conn:
            row = conn.execute(
                "SELECT * FROM archived_tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
            if not row:
                return False
            cols = [c for c in row if c != "archived_at"]
            values = [row[c] for c in cols]
            conn.execute("DELETE FROM archived_tasks WHERE task_id = ?", (task_id,))
            placeholders = ",".join("?" * len(cols))
            conn.execute(
                f"INSERT INTO tasks ({','.join(cols)}) VALUES ({placeholders})",
                values,
            )
        return True

    def list_archived(
        self,
        *,
        status: str | None = None,
        backend: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[TaskInfo]:
        """List archived tasks, newest-first by ``submit_time``."""
        from uniqc.backend_adapter.task.store import _row_to_info

        conditions: list[str] = []
        params: list[Any] = []
        if status is not None:
            conditions.append("status = ?")
            params.append(status)
        if backend is not None:
            conditions.append("backend = ?")
            params.append(backend)
        sql = "SELECT * FROM archived_tasks"
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
        with self._store._tx() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_row_to_info(row) for row in rows]

    def get_archived(self, task_id: str) -> TaskInfo | None:
        """Return an archived task by id, or ``None``."""
        from uniqc.backend_adapter.task.store import _row_to_info

        with self._store._tx() as conn:
            row = conn.execute(
                "SELECT * FROM archived_tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
        return _row_to_info(row) if row is not None else None

    def delete_archived(self, task_id: str) -> bool:
        """Permanently remove an archived task. Returns ``True`` if it existed."""
        with self._store._tx() as conn:
            cur = conn.execute(
                "DELETE FROM archived_tasks WHERE task_id = ?", (task_id,)
            )
            return cur.rowcount > 0

    def count_archived(self, *, status: str | None = None, backend: str | None = None) -> int:
        """Return total number of archived tasks."""
        conditions: list[str] = []
        params: list[Any] = []
        if status is not None:
            conditions.append("status = ?")
            params.append(status)
        if backend is not None:
            conditions.append("backend = ?")
            params.append(backend)
        sql = "SELECT COUNT(*) AS c FROM archived_tasks"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        with self._store._tx() as conn:
            row = conn.execute(sql, params).fetchone()
        return int(row["c"]) if row is not None else 0
