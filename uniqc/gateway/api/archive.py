"""Archive management API — /api/archive and /api/tasks/{id}/archive."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from uniqc.backend_adapter.task.store import TaskStore
from uniqc.gateway.db.archive_store import ArchiveStore

router = APIRouter()


def _info_to_dict(t: Any) -> dict[str, Any]:
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


# ---------------------------------------------------------------------------
# /api/tasks/{task_id}/archive  — archive a task
# ---------------------------------------------------------------------------

_archive_move_router = APIRouter(prefix="/tasks", tags=["tasks"])


@_archive_move_router.post("/{task_id}/archive")
def archive_task(task_id: str) -> dict[str, str]:
    """Move a task from the active ``tasks`` table into the archive."""
    store = TaskStore()
    task = store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    archive = ArchiveStore()
    success = archive.archive_task(task_id)
    if not success:
        raise HTTPException(
            status_code=500, detail=f"Failed to archive task '{task_id}'"
        )
    return {"archived": task_id}


# ---------------------------------------------------------------------------
# /api/archive — browse / manage archived tasks
# ---------------------------------------------------------------------------

_archive_router = APIRouter(prefix="/archive", tags=["archive"])


@_archive_router.get("")
def list_archived(
    status: str | None = None,
    backend: str | None = None,
    limit: int | None = 100,
    offset: int | None = 0,
) -> dict[str, Any]:
    """List archived tasks."""
    archive = ArchiveStore()
    tasks = archive.list_archived(status=status, backend=backend, limit=limit, offset=offset)
    return {
        "tasks": [_info_to_dict(t) for t in tasks],
        "total": archive.count_archived(status=status, backend=backend),
        "count": archive.count_archived(),
        "limit": limit,
        "offset": offset or 0,
    }


@_archive_router.get("/{task_id}")
def get_archived(task_id: str) -> dict[str, Any]:
    """Return full details of an archived task."""
    archive = ArchiveStore()
    task = archive.get_archived(task_id)
    if task is None:
        raise HTTPException(
            status_code=404, detail=f"Archived task '{task_id}' not found"
        )
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


@_archive_router.delete("/{task_id}")
def delete_archived(task_id: str) -> dict[str, str]:
    """Permanently delete an archived task."""
    archive = ArchiveStore()
    deleted = archive.delete_archived(task_id)
    if not deleted:
        raise HTTPException(
            status_code=404, detail=f"Archived task '{task_id}' not found"
        )
    return {"deleted": task_id}


@_archive_router.post("/restore/{task_id}")
def restore_task(task_id: str) -> dict[str, str]:
    """Restore an archived task back to the active task list."""
    archive = ArchiveStore()
    restored = archive.restore_task(task_id)
    if not restored:
        raise HTTPException(
            status_code=404, detail=f"Archived task '{task_id}' not found"
        )
    return {"restored": task_id}
