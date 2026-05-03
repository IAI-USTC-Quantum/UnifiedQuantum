"""Task listing and management API — /api/tasks."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from uniqc.backend_adapter.task.store import TERMINAL_STATUSES, TaskInfo, TaskStore
from uniqc.gateway.db.archive_store import ArchiveStore

router = APIRouter()


class TaskIdsRequest(BaseModel):
    task_ids: list[str] = Field(default_factory=list)


def _info_to_dict(t: TaskInfo) -> dict[str, Any]:
    return {
        "task_id": t.task_id,
        "backend": t.backend,
        "status": t.status,
        "shots": t.shots,
        "submit_time": t.submit_time,
        "update_time": t.update_time,
        "has_result": t.result is not None,
        "metadata": t.metadata,
        "archived_at": t.archived_at,
    }


@router.get("")
def list_tasks(
    status: str | None = None,
    backend: str | None = None,
    limit: int | None = 100,
    offset: int | None = 0,
) -> dict[str, Any]:
    """List active (non-archived) tasks.

    Query params:
        status: filter by task status (pending/running/success/failed/cancelled)
        backend: filter by backend name
        limit: max rows returned (default 100)
        offset: number of matching rows to skip
    """
    store = TaskStore()
    tasks = store.list(status=status, backend=backend, limit=limit, offset=offset)
    return {
        "tasks": [_info_to_dict(t) for t in tasks],
        "total": store.count(status=status, backend=backend),
        "limit": limit,
        "offset": offset or 0,
    }


@router.get("/counts")
def task_counts() -> dict[str, int]:
    """Return count of active tasks grouped by status."""
    store = TaskStore()
    statuses = ["pending", "running", "success", "failed", "cancelled"]
    result: dict[str, int] = {}
    for s in statuses:
        result[s] = store.count(status=s)
    result["total"] = sum(result.values())
    return result


@router.get("/{task_id}")
def get_task(task_id: str) -> dict[str, Any]:
    """Return full task details including result."""
    store = TaskStore()
    task = store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return {
        "task_id": task.task_id,
        "backend": task.backend,
        "status": task.status,
        "shots": task.shots,
        "submit_time": task.submit_time,
        "update_time": task.update_time,
        "result": task.result,
        "metadata": task.metadata,
        "archived_at": task.archived_at,
    }


@router.delete("/{task_id}")
def delete_task(task_id: str) -> dict[str, str]:
    """Permanently delete a task."""
    store = TaskStore()
    deleted = store.delete(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return {"deleted": task_id}


@router.post("/bulk-delete")
def bulk_delete_tasks(payload: TaskIdsRequest) -> dict[str, Any]:
    """Permanently delete active tasks by id."""
    store = TaskStore()
    deleted: list[str] = []
    missing: list[str] = []
    for task_id in payload.task_ids:
        if store.delete(task_id):
            deleted.append(task_id)
        else:
            missing.append(task_id)
    return {"deleted": deleted, "missing": missing, "count": len(deleted)}


@router.post("/bulk-archive")
def bulk_archive_tasks(payload: TaskIdsRequest) -> dict[str, Any]:
    """Move active tasks into the archive by id."""
    archive = ArchiveStore()
    archived: list[str] = []
    missing: list[str] = []
    for task_id in payload.task_ids:
        if archive.archive_task(task_id):
            archived.append(task_id)
        else:
            missing.append(task_id)
    return {"archived": archived, "missing": missing, "count": len(archived)}


def _parse_time(value: str) -> datetime | None:
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


@router.post("/archive-expired")
def archive_expired_tasks(
    hours: int = 72,
    terminal_only: bool = True,
) -> dict[str, Any]:
    """Archive active tasks older than ``hours``.

    By default only terminal tasks are archived, so pending/running jobs are not
    hidden from the active task view.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    store = TaskStore()
    archive = ArchiveStore()
    candidates = store.list(limit=None)
    archived: list[str] = []
    skipped_running: list[str] = []
    for task in candidates:
        if terminal_only and task.status not in TERMINAL_STATUSES:
            skipped_running.append(task.task_id)
            continue
        timestamp = _parse_time(task.update_time or task.submit_time)
        if timestamp is None or timestamp > cutoff:
            continue
        if archive.archive_task(task.task_id):
            archived.append(task.task_id)
    return {
        "archived": archived,
        "count": len(archived),
        "hours": hours,
        "terminal_only": terminal_only,
        "skipped_running": skipped_running,
    }
