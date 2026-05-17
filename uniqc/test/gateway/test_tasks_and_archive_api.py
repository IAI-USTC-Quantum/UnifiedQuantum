"""Tests for ``uniqc.gateway.api.tasks`` and ``uniqc.gateway.api.archive``,
plus the underlying ``ArchiveStore``.

All tests use an isolated SQLite store via the ``isolated_task_db`` fixture
in ``conftest.py``.
"""

from __future__ import annotations

from uniqc.backend_adapter.task.store import TaskInfo, TaskStatus, TaskStore
from uniqc.gateway.db.archive_store import ArchiveStore


def _make_task(task_id: str = "t1", status: str = TaskStatus.SUCCESS) -> TaskInfo:
    return TaskInfo(
        task_id=task_id,
        backend="dummy:local:simulator",
        status=status,
        shots=100,
        result={"00": 50, "11": 50},
        metadata={"submitted_by": "test"},
    )


# ---------------------------------------------------------------------------
# ArchiveStore direct unit tests
# ---------------------------------------------------------------------------


def test_archive_store_archives_and_lists(isolated_task_db):
    store = TaskStore()
    store.save(_make_task("a1"))
    store.save(_make_task("a2"))

    archive = ArchiveStore()
    assert archive.archive_task("a1") is True
    assert archive.archive_task("a2") is True
    # Second archive of the same task returns False (no live row)
    assert archive.archive_task("a1") is False

    listed = archive.list_archived()
    assert {t.task_id for t in listed} == {"a1", "a2"}
    assert archive.count_archived() == 2


def test_archive_store_get_returns_full_info(isolated_task_db):
    store = TaskStore()
    store.save(_make_task("a1"))
    ArchiveStore().archive_task("a1")

    got = ArchiveStore().get_archived("a1")
    assert got is not None
    assert got.task_id == "a1"
    assert got.result == {"00": 50, "11": 50}
    assert got.archived_at is not None


def test_archive_store_get_missing(isolated_task_db):
    assert ArchiveStore().get_archived("ghost") is None


def test_archive_store_filter_by_status_and_backend(isolated_task_db):
    store = TaskStore()
    store.save(_make_task("ok", status=TaskStatus.SUCCESS))
    store.save(_make_task("bad", status=TaskStatus.FAILED))
    archive = ArchiveStore()
    archive.archive_task("ok")
    archive.archive_task("bad")

    assert {t.task_id for t in archive.list_archived(status="success")} == {"ok"}
    assert archive.count_archived(status="success") == 1
    assert archive.count_archived(backend="dummy:local:simulator") == 2
    assert archive.count_archived(backend="not-real") == 0


def test_archive_store_delete(isolated_task_db):
    store = TaskStore()
    store.save(_make_task("a1"))
    ArchiveStore().archive_task("a1")

    assert ArchiveStore().delete_archived("a1") is True
    assert ArchiveStore().get_archived("a1") is None
    # Deleting twice returns False
    assert ArchiveStore().delete_archived("a1") is False


def test_archive_store_restore(isolated_task_db):
    store = TaskStore()
    store.save(_make_task("a1"))
    ArchiveStore().archive_task("a1")
    assert store.get("a1") is None

    assert ArchiveStore().restore_task("a1") is True
    assert store.get("a1") is not None
    assert ArchiveStore().get_archived("a1") is None
    # Restoring a missing task → False
    assert ArchiveStore().restore_task("ghost") is False


def test_archive_store_pagination(isolated_task_db):
    store = TaskStore()
    archive = ArchiveStore()
    for i in range(5):
        store.save(_make_task(f"p{i}"))
        archive.archive_task(f"p{i}")

    page1 = archive.list_archived(limit=2, offset=0)
    page2 = archive.list_archived(limit=2, offset=2)
    assert len(page1) == 2
    assert len(page2) == 2
    assert {t.task_id for t in page1}.isdisjoint({t.task_id for t in page2})


# ---------------------------------------------------------------------------
# /api/archive endpoints via TestClient
# ---------------------------------------------------------------------------


def test_archive_endpoint_archive_then_list(fastapi_client, isolated_task_db):
    TaskStore().save(_make_task("api1"))

    r = fastapi_client.post("/api/tasks/api1/archive")
    assert r.status_code == 200
    assert r.json() == {"archived": "api1"}

    r = fastapi_client.get("/api/archive")
    assert r.status_code == 200
    body = r.json()
    assert any(t["task_id"] == "api1" for t in body["tasks"])
    assert body["total"] >= 1


def test_archive_endpoint_archive_missing_task(fastapi_client, isolated_task_db):
    r = fastapi_client.post("/api/tasks/missing/archive")
    assert r.status_code == 404


def test_archive_endpoint_get_returns_result(fastapi_client, isolated_task_db):
    TaskStore().save(_make_task("g1"))
    ArchiveStore().archive_task("g1")

    r = fastapi_client.get("/api/archive/g1")
    assert r.status_code == 200, r.text
    assert r.json()["result"] == {"00": 50, "11": 50}


def test_archive_endpoint_get_missing(fastapi_client, isolated_task_db):
    r = fastapi_client.get("/api/archive/ghost")
    assert r.status_code == 404


def test_archive_endpoint_delete(fastapi_client, isolated_task_db):
    TaskStore().save(_make_task("d1"))
    ArchiveStore().archive_task("d1")

    r = fastapi_client.delete("/api/archive/d1")
    assert r.status_code == 200
    assert r.json() == {"deleted": "d1"}
    # Second delete → 404
    assert fastapi_client.delete("/api/archive/d1").status_code == 404


def test_archive_endpoint_restore(fastapi_client, isolated_task_db):
    TaskStore().save(_make_task("r1"))
    ArchiveStore().archive_task("r1")

    r = fastapi_client.post("/api/archive/restore/r1")
    assert r.status_code == 200
    assert r.json() == {"restored": "r1"}
    # Original task is back in the live store
    assert TaskStore().get("r1") is not None


def test_archive_endpoint_restore_missing(fastapi_client, isolated_task_db):
    r = fastapi_client.post("/api/archive/restore/ghost")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# /api/tasks endpoints
# ---------------------------------------------------------------------------


def test_tasks_endpoint_list_and_get(fastapi_client, isolated_task_db):
    TaskStore().save(_make_task("t1"))
    TaskStore().save(_make_task("t2", status=TaskStatus.FAILED))

    r = fastapi_client.get("/api/tasks")
    assert r.status_code == 200, r.text
    body = r.json()
    ids = [t["task_id"] for t in body["tasks"]]
    assert {"t1", "t2"}.issubset(set(ids))


def test_tasks_endpoint_counts(fastapi_client, isolated_task_db):
    TaskStore().save(_make_task("a", status=TaskStatus.SUCCESS))
    TaskStore().save(_make_task("b", status=TaskStatus.SUCCESS))
    TaskStore().save(_make_task("c", status=TaskStatus.FAILED))

    r = fastapi_client.get("/api/tasks/counts")
    assert r.status_code == 200
    counts = r.json()
    assert counts["success"] == 2
    assert counts["failed"] == 1


def test_tasks_endpoint_get_one(fastapi_client, isolated_task_db):
    TaskStore().save(_make_task("only"))
    r = fastapi_client.get("/api/tasks/only")
    assert r.status_code == 200
    assert r.json()["task_id"] == "only"


def test_tasks_endpoint_get_missing(fastapi_client, isolated_task_db):
    r = fastapi_client.get("/api/tasks/ghost")
    assert r.status_code == 404


def test_tasks_endpoint_delete(fastapi_client, isolated_task_db):
    TaskStore().save(_make_task("k1"))
    r = fastapi_client.delete("/api/tasks/k1")
    assert r.status_code == 200
    assert TaskStore().get("k1") is None


def test_tasks_endpoint_bulk_delete(fastapi_client, isolated_task_db):
    TaskStore().save(_make_task("b1"))
    TaskStore().save(_make_task("b2"))
    r = fastapi_client.post("/api/tasks/bulk-delete", json={"task_ids": ["b1", "b2"]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("deleted") == 2 or body.get("count") == 2 or "deleted" in body


def test_tasks_endpoint_bulk_archive(fastapi_client, isolated_task_db):
    TaskStore().save(_make_task("ba1"))
    TaskStore().save(_make_task("ba2"))
    r = fastapi_client.post("/api/tasks/bulk-archive", json={"task_ids": ["ba1", "ba2"]})
    assert r.status_code == 200, r.text
    assert ArchiveStore().count_archived() >= 2
