"""Regression matrix for persisted task lifecycle failures and restarts."""

from __future__ import annotations

from pathlib import Path

import pytest

import uniqc.backend_adapter.task_manager as tm
from uniqc.backend_adapter.task.store import TaskInfo, TaskShard, TaskStatus, TaskStore
from uniqc.circuit_builder import Circuit
from uniqc.exceptions import BackendNotAvailableError, BackendNotFoundError


@pytest.fixture
def isolated_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TaskStore:
    monkeypatch.setattr("uniqc.backend_adapter.task.store.DEFAULT_CACHE_DIR", tmp_path)
    store = TaskStore(cache_dir=tmp_path)
    tm._store_singleton = store
    yield store
    tm._store_singleton = None


@pytest.fixture
def circuit() -> Circuit:
    value = Circuit(1)
    value.h(0)
    value.measure(0)
    return value


@pytest.fixture
def bypass_preparation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("uniqc.backend_adapter.preflight.ensure_backend_ready", lambda _backend: None)
    monkeypatch.setattr(
        tm,
        "_prepare_circuit_for_submission",
        lambda value, _backend, _kwargs, *, local_compile: (value, {}),
    )


def _only_parent(store: TaskStore) -> TaskInfo:
    tasks = store.list()
    assert len(tasks) == 1
    return tasks[0]


class _CircuitAdapter:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error

    def adapt(self, circuit: Circuit):
        if self.error is not None:
            raise self.error
        return circuit

    def adapt_batch(self, circuits: list[Circuit]):
        if self.error is not None:
            raise self.error
        return circuits


class _TaskAdapter:
    max_native_batch_size = 1


class _Backend:
    def __init__(
        self,
        *,
        available: bool = True,
        availability_error: Exception | None = None,
        submit_error: Exception | None = None,
        batch_results: list[str | Exception] | None = None,
    ) -> None:
        self.available = available
        self.availability_error = availability_error
        self.submit_error = submit_error
        self.batch_results = list(batch_results or [])
        self.adapter = _TaskAdapter()

    def is_available(self) -> bool:
        if self.availability_error is not None:
            raise self.availability_error
        return self.available

    def submit(self, _circuit, *, shots: int, **_kwargs) -> str:
        if self.submit_error is not None:
            raise self.submit_error
        return "platform-single"

    def submit_batch(self, _circuits, *, shots: int, **_kwargs) -> str:
        result = self.batch_results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def test_backend_resolution_failure_marks_parent_failed(
    isolated_store: TaskStore,
    circuit: Circuit,
    bypass_preparation: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tm.backend_module, "get_backend", lambda _backend: (_ for _ in ()).throw(ValueError("missing")))

    with pytest.raises(BackendNotFoundError):
        tm.submit_task(circuit, backend="originq:test")

    parent = _only_parent(isolated_store)
    assert parent.status == TaskStatus.FAILED.value
    assert "backend resolution" in (parent.error_message or "")


@pytest.mark.parametrize(
    "backend,expected_exception",
    [
        (_Backend(available=False), BackendNotAvailableError),
        (_Backend(availability_error=RuntimeError("availability exploded")), RuntimeError),
    ],
)
def test_availability_failures_mark_parent_failed(
    isolated_store: TaskStore,
    circuit: Circuit,
    bypass_preparation: None,
    monkeypatch: pytest.MonkeyPatch,
    backend: _Backend,
    expected_exception: type[Exception],
) -> None:
    monkeypatch.setattr(tm.backend_module, "get_backend", lambda _backend: backend)

    with pytest.raises(expected_exception):
        tm.submit_task(circuit, backend="originq:test")

    parent = _only_parent(isolated_store)
    assert parent.status == TaskStatus.FAILED.value
    assert "availability" in (parent.error_message or "")


def test_adaptation_failure_marks_parent_failed(
    isolated_store: TaskStore,
    circuit: Circuit,
    bypass_preparation: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tm.backend_module, "get_backend", lambda _backend: _Backend())
    monkeypatch.setattr(tm, "_get_adapter", lambda _backend: _CircuitAdapter(RuntimeError("adapt exploded")))

    with pytest.raises(RuntimeError, match="adapt exploded"):
        tm.submit_task(circuit, backend="originq:test")

    parent = _only_parent(isolated_store)
    assert parent.status == TaskStatus.FAILED.value
    assert "adaptation" in (parent.error_message or "")


def test_submit_failure_marks_parent_failed(
    isolated_store: TaskStore,
    circuit: Circuit,
    bypass_preparation: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = _Backend(submit_error=RuntimeError("submit exploded"))
    monkeypatch.setattr(tm.backend_module, "get_backend", lambda _backend: backend)
    monkeypatch.setattr(tm, "_get_adapter", lambda _backend: _CircuitAdapter())

    with pytest.raises(RuntimeError, match="submit exploded"):
        tm.submit_task(circuit, backend="originq:test")

    parent = _only_parent(isolated_store)
    assert parent.status == TaskStatus.FAILED.value
    assert "submission" in (parent.error_message or "")


def test_shard_persistence_failure_marks_parent_failed(
    isolated_store: TaskStore,
    circuit: Circuit,
    bypass_preparation: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tm.backend_module, "get_backend", lambda _backend: _Backend())
    monkeypatch.setattr(tm, "_get_adapter", lambda _backend: _CircuitAdapter())
    monkeypatch.setattr(
        TaskStore,
        "save_shard",
        lambda _self, _shard: (_ for _ in ()).throw(RuntimeError("disk full")),
    )

    with pytest.raises(RuntimeError, match="disk full"):
        tm.submit_task(circuit, backend="originq:test")

    parent = _only_parent(isolated_store)
    assert parent.status == TaskStatus.FAILED.value
    assert "shard persistence" in (parent.error_message or "")
    assert parent.metadata["platform_task_id"] == "platform-single"


def test_batch_adaptation_failure_marks_parent_failed(
    isolated_store: TaskStore,
    circuit: Circuit,
    bypass_preparation: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tm.backend_module, "get_backend", lambda _backend: _Backend())
    monkeypatch.setattr(tm, "_get_adapter", lambda _backend: _CircuitAdapter(RuntimeError("batch adapt exploded")))

    with pytest.raises(RuntimeError, match="batch adapt exploded"):
        tm.submit_batch([circuit, circuit], backend="originq:test")

    parent = _only_parent(isolated_store)
    assert parent.status == TaskStatus.FAILED.value
    assert "adaptation" in (parent.error_message or "")


def test_batch_backend_resolution_failure_marks_parent_failed(
    isolated_store: TaskStore,
    circuit: Circuit,
    bypass_preparation: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tm.backend_module, "get_backend", lambda _backend: (_ for _ in ()).throw(ValueError("missing")))

    with pytest.raises(BackendNotFoundError):
        tm.submit_batch([circuit, circuit], backend="originq:test")

    parent = _only_parent(isolated_store)
    assert parent.status == TaskStatus.FAILED.value
    assert "backend resolution" in (parent.error_message or "")


@pytest.mark.parametrize(
    "backend,expected_exception",
    [
        (_Backend(available=False), BackendNotAvailableError),
        (_Backend(availability_error=RuntimeError("batch availability exploded")), RuntimeError),
    ],
)
def test_batch_availability_failures_mark_parent_failed(
    isolated_store: TaskStore,
    circuit: Circuit,
    bypass_preparation: None,
    monkeypatch: pytest.MonkeyPatch,
    backend: _Backend,
    expected_exception: type[Exception],
) -> None:
    monkeypatch.setattr(tm.backend_module, "get_backend", lambda _backend: backend)

    with pytest.raises(expected_exception):
        tm.submit_batch([circuit, circuit], backend="originq:test")

    parent = _only_parent(isolated_store)
    assert parent.status == TaskStatus.FAILED.value
    assert "availability" in (parent.error_message or "")


def test_batch_adapter_initialization_failure_marks_parent_failed(
    isolated_store: TaskStore,
    circuit: Circuit,
    bypass_preparation: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Backend:
        def is_available(self):
            return True

        @property
        def adapter(self):
            raise RuntimeError("adapter init exploded")

    monkeypatch.setattr(tm.backend_module, "get_backend", lambda _backend: Backend())
    monkeypatch.setattr(tm, "_get_adapter", lambda _backend: _CircuitAdapter())

    with pytest.raises(RuntimeError, match="adapter init exploded"):
        tm.submit_batch([circuit, circuit], backend="originq:test")

    parent = _only_parent(isolated_store)
    assert parent.status == TaskStatus.FAILED.value
    assert "adapter initialization" in (parent.error_message or "")


def test_batch_shard_persistence_failure_marks_parent_failed(
    isolated_store: TaskStore,
    circuit: Circuit,
    bypass_preparation: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = _Backend(batch_results=["platform-0"])
    monkeypatch.setattr(tm.backend_module, "get_backend", lambda _backend: backend)
    monkeypatch.setattr(tm, "_get_adapter", lambda _backend: _CircuitAdapter())
    monkeypatch.setattr(
        TaskStore,
        "save_shard",
        lambda _self, _shard: (_ for _ in ()).throw(RuntimeError("batch disk full")),
    )

    with pytest.raises(RuntimeError, match="batch disk full"):
        tm.submit_batch([circuit], backend="originq:test")

    parent = _only_parent(isolated_store)
    assert parent.status == TaskStatus.FAILED.value
    assert "shard persistence" in (parent.error_message or "")
    assert parent.metadata["unpersisted_platform_task_ids"] == ["platform-0"]


def test_partial_batch_submission_persists_failed_parent_and_submitted_shards(
    isolated_store: TaskStore,
    circuit: Circuit,
    bypass_preparation: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = _Backend(batch_results=["platform-0", RuntimeError("second shard exploded")])
    monkeypatch.setattr(tm.backend_module, "get_backend", lambda _backend: backend)
    monkeypatch.setattr(tm, "_get_adapter", lambda _backend: _CircuitAdapter())

    with pytest.raises(RuntimeError, match="second shard exploded"):
        tm.submit_batch([circuit, circuit], backend="originq:test")

    parent = _only_parent(isolated_store)
    assert parent.status == TaskStatus.FAILED.value
    assert parent.metadata["partial_submitted_shards"] == ["platform-0"]
    assert [shard.platform_task_id for shard in isolated_store.get_shards(parent.task_id)] == ["platform-0"]


def test_timeout_final_query_uses_persisted_platform_id(
    isolated_store: TaskStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = TaskInfo(
        task_id="uqt_timeout",
        backend="originq:test",
        status=TaskStatus.RUNNING,
        shots=100,
    )
    isolated_store.save(parent)
    isolated_store.save_shard(
        TaskShard(
            uniqc_task_id=parent.task_id,
            shard_index=0,
            platform_task_id="platform-timeout",
            backend=parent.backend,
            status=TaskStatus.RUNNING,
        )
    )
    queried: list[str] = []

    class Backend:
        adapter = object()

        def query(self, task_id: str):
            queried.append(task_id)
            if len(queried) == 1:
                return {"status": "running"}
            return {"status": "success", "result": {"0": 100}}

    monkeypatch.setattr(tm.backend_module, "get_backend", lambda _backend: Backend())

    result = tm.wait_for_result(parent.task_id, timeout=0, poll_interval=0)
    assert result == {"0": 100}
    assert queried == ["platform-timeout", "platform-timeout"]


def test_refresh_restores_native_batch_query_context_after_restart(
    isolated_store: TaskStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = TaskInfo(
        task_id="uqt_restart",
        backend="originq:test",
        status=TaskStatus.RUNNING,
        shots=2048,
        metadata={"batch": True, "batch_size": 2},
    )
    isolated_store.save(parent)
    shard = TaskShard(
        uniqc_task_id=parent.task_id,
        shard_index=0,
        platform_task_id="originq-batch",
        backend=parent.backend,
        circuit_count=2,
        status=TaskStatus.RUNNING,
    )
    isolated_store.save_shard(shard)
    restored: list[tuple[str, int, int]] = []

    class Adapter:
        def restore_batch_context(self, task_id: str, circuit_count: int, shots: int) -> None:
            restored.append((task_id, circuit_count, shots))

    class Backend:
        adapter = Adapter()

        def query(self, _task_id: str):
            return {"status": "success", "result": [{"0": 2048}, {"1": 2048}]}

    monkeypatch.setattr(tm.backend_module, "get_backend", lambda _backend: Backend())

    refreshed = tm._refresh_shard_from_backend(shard)
    assert restored == [("originq-batch", 2, 2048)]
    assert refreshed.result == [{"0": 2048}, {"1": 2048}]


def test_originq_query_uses_restored_batch_context_after_fresh_adapter() -> None:
    from uniqc.backend_adapter.task.adapters import OriginQAdapter

    class FakeResult:
        def job_status(self):
            return type("Status", (), {"name": "FINISHED"})()

        def error_message(self):
            return ""

        def get_counts_list(self):
            return [{"00": 100}, {"11": 100}]

        def get_counts(self):
            return {"00": 100}

    class FakeJob:
        def __init__(self, task_id):
            self.task_id = task_id

        def query(self):
            return FakeResult()

    adapter = OriginQAdapter.__new__(OriginQAdapter)
    adapter._batch_job_sizes = {}
    adapter._ensure_imports = lambda: None
    adapter._QCloudJob = FakeJob
    adapter.restore_batch_context("BATCH-RESTART", circuit_count=2, shots=100)

    result = adapter.query("BATCH-RESTART")
    assert result["status"] == "success"
    assert result["result"] == [{"00": 100}, {"11": 100}]
