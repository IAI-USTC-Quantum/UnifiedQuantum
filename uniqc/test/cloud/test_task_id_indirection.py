"""Tests for the uniqc task-id indirection layer.

Covers:

* uqt_ id allocation, format, and recognizer
* TaskShard CRUD + FK cascade behaviour
* Status aggregation rules
* Submit / query / wait flow against the dummy backend
* Legacy platform-id alias with DeprecationWarning
* Archive cascade via gateway ArchiveStore
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest

from uniqc.backend_adapter.task.store import (
    TERMINAL_STATUSES,
    TaskInfo,
    TaskShard,
    TaskStatus,
    TaskStore,
    UNIQC_TASK_ID_PREFIX,
    generate_uniqc_task_id,
    is_uniqc_task_id,
)


@pytest.fixture
def tmp_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TaskStore:
    """Provide an isolated TaskStore + module-global redirect."""
    monkeypatch.setattr(
        "uniqc.backend_adapter.task.store.DEFAULT_CACHE_DIR", tmp_path
    )
    # Reset the module-global cached store used by task_manager._store().
    import uniqc.backend_adapter.task_manager as tm
    tm._store_singleton = None  # type: ignore[attr-defined]
    return TaskStore(cache_dir=tmp_path)


# ---------------------------------------------------------------------------
# id helpers
# ---------------------------------------------------------------------------


def test_generate_uniqc_task_id_format():
    uid = generate_uniqc_task_id()
    assert uid.startswith(UNIQC_TASK_ID_PREFIX)
    assert len(uid) == len(UNIQC_TASK_ID_PREFIX) + 32
    assert is_uniqc_task_id(uid)


def test_is_uniqc_task_id_rejects_other_formats():
    assert not is_uniqc_task_id("ABC123DEADBEEF")
    assert not is_uniqc_task_id("not_uqt_xyz")
    assert not is_uniqc_task_id("")


# ---------------------------------------------------------------------------
# Shard CRUD + cascade
# ---------------------------------------------------------------------------


def _seed_parent(store: TaskStore, uid: str | None = None) -> str:
    uid = uid or generate_uniqc_task_id()
    store.save(
        TaskInfo(task_id=uid, backend="dummy:local:virtual-line-2",
                 status=TaskStatus.PENDING, shots=100)
    )
    return uid


def test_save_and_get_shards(tmp_store: TaskStore):
    uid = _seed_parent(tmp_store)
    for i in range(3):
        tmp_store.save_shard(TaskShard(
            uniqc_task_id=uid,
            shard_index=i,
            platform_task_id=f"plat_{i}",
            backend="dummy:local:virtual-line-2",
            circuit_count=1,
            sub_index_offset=i,
            status=TaskStatus.RUNNING.value,
        ))
    shards = tmp_store.get_shards(uid)
    assert len(shards) == 3
    assert [s.shard_index for s in shards] == [0, 1, 2]


def test_fk_cascade_on_parent_delete(tmp_store: TaskStore):
    uid = _seed_parent(tmp_store)
    tmp_store.save_shard(TaskShard(
        uniqc_task_id=uid, shard_index=0, platform_task_id="p0",
        backend="dummy:local:virtual-line-2", circuit_count=1,
        sub_index_offset=0, status=TaskStatus.SUCCESS.value,
    ))
    assert len(tmp_store.get_shards(uid)) == 1
    tmp_store.delete(uid)
    assert tmp_store.get_shards(uid) == []


def test_find_uniqc_id_by_platform_id(tmp_store: TaskStore):
    uid = _seed_parent(tmp_store)
    tmp_store.save_shard(TaskShard(
        uniqc_task_id=uid, shard_index=0, platform_task_id="cloud-job-XYZ",
        backend="dummy:local:virtual-line-2", circuit_count=1,
        sub_index_offset=0, status=TaskStatus.RUNNING.value,
    ))
    assert tmp_store.find_uniqc_id_by_platform_id("cloud-job-XYZ") == uid
    assert tmp_store.find_uniqc_id_by_platform_id("missing") is None


# ---------------------------------------------------------------------------
# Status aggregation rules
# ---------------------------------------------------------------------------


def _shard(status: str) -> TaskShard:
    return TaskShard(
        uniqc_task_id="x", shard_index=0, platform_task_id="p",
        backend="b", circuit_count=1, sub_index_offset=0, status=status,
    )


@pytest.mark.parametrize("statuses,expected", [
    ([], "pending"),
    (["running"], "running"),
    (["pending", "success"], "running"),
    (["success", "success"], "success"),
    (["success", "failed"], "failed"),
    (["failed", "cancelled"], "failed"),
    (["cancelled", "success"], "cancelled"),
    (["cancelled", "cancelled"], "cancelled"),
])
def test_aggregate_status(statuses, expected):
    shards = [_shard(s) for s in statuses]
    assert TaskStore.aggregate_status(shards) == expected


# ---------------------------------------------------------------------------
# Submit / query / wait via dummy backend
# ---------------------------------------------------------------------------


def _make_bell():
    from uniqc.circuit_builder import Circuit
    c = Circuit(2); c.h(0); c.cnot(0, 1); c.measure(0, 1)
    return c


def test_submit_task_returns_uqt_id_with_one_shard(tmp_store):
    from uniqc import submit_task, get_platform_task_ids
    uid = submit_task(_make_bell(), backend="dummy:local:virtual-line-2", shots=50)
    assert is_uniqc_task_id(uid)
    shards = get_platform_task_ids(uid)
    assert len(shards) == 1 and shards[0].circuit_count == 1


def test_submit_batch_one_shard_per_circuit_for_dummy(tmp_store):
    from uniqc import submit_batch, get_platform_task_ids, wait_for_result
    circuits = [_make_bell() for _ in range(4)]
    uid = submit_batch(circuits, backend="dummy:local:virtual-line-2", shots=50)
    assert is_uniqc_task_id(uid)
    shards = get_platform_task_ids(uid)
    assert len(shards) == 4
    for i, s in enumerate(shards):
        assert s.shard_index == i and s.sub_index_offset == i
        assert s.circuit_count == 1

    results = wait_for_result(uid, timeout=10, poll_interval=1)
    assert isinstance(results, list) and len(results) == 4


def test_submit_batch_return_platform_ids(tmp_store):
    from uniqc import submit_batch
    plat_ids = submit_batch(
        [_make_bell() for _ in range(3)],
        backend="dummy:local:virtual-line-2", shots=50,
        return_platform_ids=True,
    )
    assert isinstance(plat_ids, list) and len(plat_ids) == 3


def test_legacy_platform_id_alias_emits_deprecation(tmp_store):
    from uniqc import submit_batch, get_platform_task_ids, query_task
    uid = submit_batch(
        [_make_bell() for _ in range(2)],
        backend="dummy:local:virtual-line-2", shots=50,
    )
    plat_id = get_platform_task_ids(uid)[0].platform_task_id
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        info = query_task(plat_id)
        deps = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        assert deps, "expected DeprecationWarning when looking up via platform id"
    assert is_uniqc_task_id(info.task_id)


# ---------------------------------------------------------------------------
# Error message extraction
# ---------------------------------------------------------------------------


def test_extract_error_message_handles_nested_and_flat():
    from uniqc.backend_adapter.task_manager import _extract_error_message
    assert _extract_error_message(
        {"status": "failed", "result": {"error": "bad chip"}}
    ) == "bad chip"
    assert _extract_error_message(
        {"status": "failed", "error": "auth"}
    ) == "auth"
    assert _extract_error_message({"status": "failed"}) is None


# ---------------------------------------------------------------------------
# Archive cascade
# ---------------------------------------------------------------------------


def test_archive_and_restore_preserves_shards(tmp_store):
    from uniqc.gateway.db.archive_store import ArchiveStore
    uid = _seed_parent(tmp_store)
    for i in range(2):
        tmp_store.save_shard(TaskShard(
            uniqc_task_id=uid, shard_index=i,
            platform_task_id=f"p{i}", backend="dummy:local:virtual-line-2",
            circuit_count=1, sub_index_offset=i,
            status=TaskStatus.SUCCESS.value, result={"00": 50, "11": 50},
        ))

    archive = ArchiveStore()
    assert archive.archive_task(uid)
    assert tmp_store.get_shards(uid) == []  # cascaded out of live table

    assert archive.restore_task(uid)
    restored = tmp_store.get_shards(uid)
    assert len(restored) == 2
    assert [s.platform_task_id for s in restored] == ["p0", "p1"]


def test_delete_archived_clears_shards(tmp_store):
    from uniqc.gateway.db.archive_store import ArchiveStore
    uid = _seed_parent(tmp_store)
    tmp_store.save_shard(TaskShard(
        uniqc_task_id=uid, shard_index=0, platform_task_id="p0",
        backend="dummy:local:virtual-line-2", circuit_count=1,
        sub_index_offset=0, status=TaskStatus.SUCCESS.value,
    ))
    archive = ArchiveStore()
    archive.archive_task(uid)
    assert archive.delete_archived(uid)
    # Confirm both archived tables are clean.
    with tmp_store._tx() as conn:
        n = conn.execute(
            "SELECT COUNT(*) AS c FROM archived_task_shards WHERE uniqc_task_id = ?",
            (uid,),
        ).fetchone()["c"]
    assert n == 0
