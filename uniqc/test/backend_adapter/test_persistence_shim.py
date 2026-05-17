"""Tests for the legacy ``TaskPersistence`` dict-shape compatibility shim.

This module is a thin wrapper around :class:`TaskStore`; previous coverage
was 0 % because all callers lived behind the ``cloud`` marker. These tests
exercise the wrapper directly against an isolated SQLite DB.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from uniqc.backend_adapter.task.persistence import (
    DEFAULT_CACHE_DIR,
    TaskPersistence,
)


@pytest.fixture
def persistence(tmp_path: Path) -> TaskPersistence:
    return TaskPersistence(cache_dir=tmp_path)


def test_module_exports_default_cache_dir():
    assert DEFAULT_CACHE_DIR is not None


def test_save_and_load_minimal(persistence):
    persistence.save("t1", platform="originq", status="success", result={"00": 50})
    rec = persistence.load("t1")
    assert rec is not None
    assert rec["task_id"] == "t1"
    assert rec["platform"] == "originq"
    assert rec["status"] == "success"
    assert rec["result"] == {"00": 50}


def test_save_promotes_reserved_kwargs(persistence):
    persistence.save(
        "t1",
        platform="ibm",
        status="running",
        result=None,
        shots=2048,
        submit_time="2026-05-01T00:00:00",
        custom_field="extra",
    )
    rec = persistence.load("t1")
    assert rec["shots"] == 2048
    assert rec["submit_time"] == "2026-05-01T00:00:00"
    # Free-form metadata flattens back to the top level
    assert rec["custom_field"] == "extra"


def test_load_missing_returns_none(persistence):
    assert persistence.load("ghost") is None


def test_update_existing(persistence):
    persistence.save("t1", "originq", "running")
    updated = persistence.update("t1", status="success", result={"00": 100})
    assert updated is True
    rec = persistence.load("t1")
    assert rec["status"] == "success"
    assert rec["result"] == {"00": 100}


def test_update_missing_returns_false(persistence):
    assert persistence.update("ghost", status="success") is False


def test_update_changes_platform_and_metadata(persistence):
    persistence.save("t1", "originq", "running", note="first")
    persistence.update("t1", platform="ibm", note="second", extra=42)
    rec = persistence.load("t1")
    assert rec["platform"] == "ibm"
    assert rec["note"] == "second"
    assert rec["extra"] == 42


def test_upsert_inserts_when_missing(persistence):
    persistence.upsert("new", "ibm", "pending")
    assert persistence.load("new") is not None


def test_upsert_updates_when_present(persistence):
    persistence.save("t1", "originq", "running")
    persistence.upsert("t1", "originq", "success", result={"00": 50})
    rec = persistence.load("t1")
    assert rec["status"] == "success"
    assert rec["result"] == {"00": 50}


def test_list_all_newest_first(persistence):
    persistence.save("a", "originq", "success", submit_time="2026-01-01T00:00:00")
    persistence.save("b", "originq", "failed", submit_time="2026-02-01T00:00:00")
    records = persistence.list_all()
    assert [r["task_id"] for r in records[:2]] == ["b", "a"]


def test_list_filter_by_platform(persistence):
    persistence.save("a", "originq", "success")
    persistence.save("b", "ibm", "success")
    by_originq = persistence.list_by_platform("originq")
    assert {r["task_id"] for r in by_originq} == {"a"}


def test_list_filter_by_status(persistence):
    persistence.save("a", "originq", "success")
    persistence.save("b", "originq", "failed")
    success = persistence.list_all(status="success")
    assert {r["task_id"] for r in success} == {"a"}


def test_list_pending_includes_pending_and_running(persistence):
    persistence.save("a", "originq", "pending")
    persistence.save("b", "originq", "running")
    persistence.save("c", "originq", "success")
    pending = persistence.list_pending()
    assert {r["task_id"] for r in pending} == {"a", "b"}


def test_count(persistence):
    persistence.save("a", "originq", "success")
    persistence.save("b", "originq", "success")
    persistence.save("c", "ibm", "failed")
    assert persistence.count() == 3
    assert persistence.count(platform="originq") == 2
    assert persistence.count(status="success") == 2


def test_delete(persistence):
    persistence.save("a", "originq", "success")
    assert persistence.delete("a") is True
    assert persistence.load("a") is None
    assert persistence.delete("a") is False


def test_clear_completed_removes_terminal(persistence):
    persistence.save("a", "originq", "running")
    persistence.save("b", "originq", "success")
    persistence.save("c", "originq", "failed")
    cleared = persistence.clear_completed()
    assert cleared == 2
    # Running task survives
    assert persistence.load("a") is not None
    assert persistence.load("b") is None
    assert persistence.load("c") is None


def test_tasks_file_points_at_sqlite(persistence, tmp_path):
    # Legacy alias: tasks_file should point at tasks.sqlite under cache_dir
    assert persistence.tasks_file.suffix == ".sqlite"
    assert persistence.cache_dir == tmp_path
