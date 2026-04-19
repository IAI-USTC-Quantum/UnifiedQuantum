"""Task persistence (legacy dict-based API) backed by the SQLite TaskStore.

Historically this module offered a JSONL-based ``TaskPersistence`` class.
All storage has been unified onto :class:`uniqc.task.store.TaskStore`
(SQLite); this module now provides a thin compatibility layer that keeps
the same flat-dict interface (``platform``/``status``/``result`` + extra
keyword metadata).

Usage::

    from uniqc.task.persistence import TaskPersistence

    persistence = TaskPersistence()

    # Save a task
    persistence.save(
        task_id="task-123",
        platform="originq",
        status="success",
        result={"counts": {"00": 512, "11": 488}},
        shots=1000,
    )

    # Load a task
    record = persistence.load("task-123")

    # List all tasks for a platform
    tasks = persistence.list_all(platform="originq")
"""

from __future__ import annotations

__all__ = ["TaskPersistence", "DEFAULT_CACHE_DIR"]

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from uniqc.task.store import (
    DEFAULT_CACHE_DIR as _STORE_DEFAULT_CACHE_DIR,
    TERMINAL_STATUSES,
    TaskInfo,
    TaskStore,
)

# Back-compat re-export so callers that imported this symbol keep working.
DEFAULT_CACHE_DIR: Path = _STORE_DEFAULT_CACHE_DIR


# Reserved metadata keys that map onto first-class TaskInfo fields. Any
# other keyword ends up in TaskInfo.metadata and flattened back on read.
_RESERVED_KWARGS = {"shots", "submit_time", "update_time"}


class TaskPersistence:
    """Dict-shaped task store backed by SQLite.

    The dict schema exposed to callers uses ``platform`` as the field name
    for the backend (kept for backward compatibility with pre-unification
    callers). Internally, records are stored in the shared SQLite database
    managed by :class:`TaskStore`.

    Attributes:
        cache_dir: Directory containing ``tasks.sqlite``.
        tasks_file: Path to the SQLite database (legacy name preserved for
            callers that introspect the storage file).

    Example:
        >>> persistence = TaskPersistence()
        >>> persistence.save("task-1", "originq", "running")
        >>> record = persistence.load("task-1")
        >>> print(record['status'])
        'running'
    """

    def __init__(self, cache_dir: Optional[Path] = None) -> None:
        self._store = TaskStore(cache_dir)
        self.cache_dir: Path = self._store.cache_dir
        # Legacy attribute: historically referenced the JSONL file;
        # now points at the unified SQLite database.
        self.tasks_file: Path = self._store.db_path

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _split_kwargs(metadata: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Split caller kwargs into (reserved, extra)."""
        reserved: Dict[str, Any] = {}
        extra: Dict[str, Any] = {}
        for key, value in metadata.items():
            if key in _RESERVED_KWARGS:
                reserved[key] = value
            else:
                extra[key] = value
        return reserved, extra

    @staticmethod
    def _info_to_record(info: TaskInfo) -> Dict[str, Any]:
        """Render a TaskInfo as the legacy flat-dict record."""
        record: Dict[str, Any] = {
            "task_id": info.task_id,
            "platform": info.backend,
            "status": info.status,
            "result": info.result,
            "submit_time": info.submit_time,
            "update_time": info.update_time,
        }
        if info.shots:
            record["shots"] = info.shots
        # Flatten free-form metadata back into the top level for the
        # historical record shape. Reserved keys take precedence.
        for key, value in (info.metadata or {}).items():
            record.setdefault(key, value)
        return record

    # -- write --------------------------------------------------------------

    def save(
        self,
        task_id: str,
        platform: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        **metadata: Any,
    ) -> None:
        """Save (upsert) a task record.

        Args:
            task_id: Unique task identifier.
            platform: Platform / backend name.
            status: Task status ('pending', 'running', 'success', 'failed').
            result: Optional result dict.
            **metadata: Extra fields. ``shots``, ``submit_time``,
                ``update_time`` are recognised and promoted onto TaskInfo;
                anything else is stored in ``TaskInfo.metadata``.
        """
        reserved, extra = self._split_kwargs(metadata)
        now = datetime.now().isoformat()
        info = TaskInfo(
            task_id=task_id,
            backend=platform,
            status=status,
            result=result,
            shots=int(reserved.get("shots", 0)),
            submit_time=reserved.get("submit_time", now),
            update_time=reserved.get("update_time", now),
            metadata=extra,
        )
        self._store.save(info)

    def update(self, task_id: str, **updates: Any) -> bool:
        """Update an existing record. ``update_time`` is refreshed.

        Returns ``True`` if the record existed and was updated.
        """
        existing = self._store.get(task_id)
        if existing is None:
            return False

        reserved, extra = self._split_kwargs(updates)

        if "platform" in extra:
            existing.backend = extra.pop("platform")
        if "status" in extra:
            existing.status = extra.pop("status")
        if "result" in extra:
            existing.result = extra.pop("result")

        if "shots" in reserved:
            existing.shots = int(reserved["shots"])
        if "submit_time" in reserved:
            existing.submit_time = reserved["submit_time"]
        # update_time is always refreshed by TaskStore.save()

        if extra:
            merged_metadata = dict(existing.metadata or {})
            merged_metadata.update(extra)
            existing.metadata = merged_metadata

        self._store.save(existing)
        return True

    def upsert(
        self,
        task_id: str,
        platform: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        **metadata: Any,
    ) -> None:
        """Update if present, otherwise insert."""
        if self._store.get(task_id) is not None:
            self.update(task_id, status=status, result=result, **metadata)
        else:
            self.save(task_id, platform, status, result=result, **metadata)

    # -- read ---------------------------------------------------------------

    def load(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Load a record by task id."""
        info = self._store.get(task_id)
        return self._info_to_record(info) if info is not None else None

    def list_all(
        self,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List records, newest first.

        Args:
            platform: Filter by platform / backend name.
            status: Filter by status.
            limit: Max number of records.
        """
        infos = self._store.list(status=status, backend=platform, limit=limit)
        return [self._info_to_record(i) for i in infos]

    def list_by_platform(self, platform: str) -> List[Dict[str, Any]]:
        """All records for a given platform."""
        return self.list_all(platform=platform)

    def list_pending(self) -> List[Dict[str, Any]]:
        """Records currently in-flight ('pending' or 'running')."""
        records: List[Dict[str, Any]] = []
        for status in ("pending", "running"):
            records.extend(self.list_all(status=status))
        return records

    def count(
        self, platform: Optional[str] = None, status: Optional[str] = None
    ) -> int:
        """Count records with optional filters."""
        return self._store.count(status=status, backend=platform)

    # -- delete -------------------------------------------------------------

    def clear_completed(self) -> int:
        """Remove records whose status is terminal. Returns count removed."""
        return self._store.clear_completed(TERMINAL_STATUSES)

    def delete(self, task_id: str) -> bool:
        """Delete a record by id. Returns ``True`` if it existed."""
        return self._store.delete(task_id)
