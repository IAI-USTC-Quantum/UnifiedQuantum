"""Task management with local caching for quantum computing backends.

This module provides a unified interface for submitting quantum tasks,
managing task lifecycle, and caching results locally. All persistent
storage is delegated to :class:`uniqc.task.store.TaskStore` (SQLite at
``~/.uniqc/cache/tasks.sqlite``).

Environment Variables:
    UNIQC_DUMMY: Set to 'true', '1', or 'yes' to enable dummy mode.
        When enabled, all task submissions use local simulation instead
        of real quantum backends. Useful for development and testing.

Usage::

    from uniqc.task_manager import submit_task, query_task, wait_for_result
    from uniqc.circuit_builder import Circuit
    from uniqc.backend import get_backend

    # Create a circuit
    circuit = Circuit()
    circuit.h(0)
    circuit.cnot(0, 1)
    circuit.measure(0, 1)

    # Submit task (use UNIQC_DUMMY=true for local simulation)
    task_id = submit_task(circuit, backend='quafu', shots=1000)

    # Wait for result
    result = wait_for_result(task_id, backend='quafu', timeout=300)

    # Query task status
    info = query_task(task_id, backend='quafu')
    print(info['status'])  # 'running', 'success', or 'failed'

    # Explicitly use dummy mode for a single submission
    task_id = submit_task(circuit, backend='quafu', dummy=True)
"""

from __future__ import annotations

__all__ = [
    # Task submission
    "submit_task",
    "submit_batch",
    # Task query
    "query_task",
    "wait_for_result",
    # Cache management
    "save_task",
    "get_task",
    "list_tasks",
    "clear_completed_tasks",
    "clear_cache",
    # Classes
    "TaskInfo",
    "TaskStatus",
    "TaskManager",
    # Dummy mode
    "UNIQC_DUMMY",
    "is_dummy_mode",
    # Storage path (useful for tests / tooling)
    "DEFAULT_CACHE_DIR",
]

import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from uniqc.circuit_builder.qcircuit import Circuit

from uniqc import backend as backend_module
from uniqc.circuit_adapter import (
    CircuitAdapter,
    IBMCircuitAdapter,
    OriginQCircuitAdapter,
    QuafuCircuitAdapter,
)
from uniqc.exceptions import (
    AuthenticationError,
    BackendNotAvailableError,
    BackendNotFoundError,
    InsufficientCreditsError,
    NetworkError,
    QuotaExceededError,
    TaskFailedError,
    TaskNotFoundError,
    TaskTimeoutError,
)
from uniqc.task.adapters.base import (
    TASK_STATUS_FAILED,
    TASK_STATUS_RUNNING,
    TASK_STATUS_SUCCESS,
)
from uniqc.task.store import (
    DEFAULT_CACHE_DIR,
    TaskInfo,
    TaskStatus,
    TaskStore,
)

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

# Environment variable for global dummy mode
UNIQC_DUMMY = os.environ.get("UNIQC_DUMMY", "").lower() in ("true", "1", "yes")


def is_dummy_mode() -> bool:
    """Check if dummy mode is enabled via environment variable.

    Returns:
        True if UNIQC_DUMMY is set to 'true', '1', or 'yes'.
    """
    return UNIQC_DUMMY


# -----------------------------------------------------------------------------
# Circuit Adapter Mapping
# -----------------------------------------------------------------------------

ADAPTER_MAP: dict[str, type[CircuitAdapter]] = {
    "originq": OriginQCircuitAdapter,
    "quafu": QuafuCircuitAdapter,
    "ibm": IBMCircuitAdapter,
}


def _get_adapter(backend_name: str) -> CircuitAdapter:
    """Get the appropriate circuit adapter for a backend.

    Args:
        backend_name: The name of the backend.

    Returns:
        CircuitAdapter instance for the backend.

    Raises:
        BackendNotFoundError: If no adapter exists for the backend.
    """
    if backend_name not in ADAPTER_MAP:
        available = ", ".join(ADAPTER_MAP.keys())
        raise BackendNotFoundError(
            f"No circuit adapter for backend '{backend_name}'. "
            f"Available adapters: {available}"
        )
    return ADAPTER_MAP[backend_name]()


# -----------------------------------------------------------------------------
# Cache Management
# -----------------------------------------------------------------------------

def _store(cache_dir: Path | None = None) -> TaskStore:
    """Return a :class:`TaskStore` bound to ``cache_dir`` (or the default)."""
    return TaskStore(cache_dir)


def save_task(task_info: TaskInfo, cache_dir: Path | None = None) -> None:
    """Save a task to the local cache.

    Args:
        task_info: Task information to save.
        cache_dir: Optional custom cache directory.
    """
    _store(cache_dir).save(task_info)


def get_task(task_id: str, cache_dir: Path | None = None) -> TaskInfo | None:
    """Get a task from the local cache.

    Args:
        task_id: The task identifier.
        cache_dir: Optional custom cache directory.

    Returns:
        TaskInfo if found, None otherwise.
    """
    return _store(cache_dir).get(task_id)


def list_tasks(
    status: str | None = None,
    backend: str | None = None,
    cache_dir: Path | None = None,
) -> list[TaskInfo]:
    """List tasks from the local cache.

    Args:
        status: Filter by status (optional).
        backend: Filter by backend (optional).
        cache_dir: Optional custom cache directory.

    Returns:
        List of TaskInfo objects matching the filters, newest first.
    """
    return _store(cache_dir).list(status=status, backend=backend)


def clear_completed_tasks(cache_dir: Path | None = None) -> int:
    """Remove completed tasks from the cache.

    Args:
        cache_dir: Optional custom cache directory.

    Returns:
        Number of tasks removed.
    """
    return _store(cache_dir).clear_completed()


def clear_cache(cache_dir: Path | None = None) -> None:
    """Clear all tasks from the cache by deleting the SQLite file.

    Args:
        cache_dir: Optional custom cache directory.
    """
    _store(cache_dir).clear_all()


# -----------------------------------------------------------------------------
# Error Handling
# -----------------------------------------------------------------------------

def _map_adapter_error(error: Exception, backend_name: str) -> Exception:
    """Map an adapter error to a UnifiedQuantumError.

    Args:
        error: The original error from the adapter.
        backend_name: The name of the backend.

    Returns:
        A UnifiedQuantumError subclass or the original error.
    """
    error_message = str(error).lower()

    # Check for authentication errors
    if any(keyword in error_message for keyword in ["unauthorized", "invalid token", "authentication", "auth"]):
        return AuthenticationError(
            f"Authentication failed for backend '{backend_name}'. "
            "Please check your API token or credentials.",
            details={"original_error": str(error)},
        )

    # Check for credit/quota errors
    if any(keyword in error_message for keyword in ["credit", "balance", "payment", "billing"]):
        return InsufficientCreditsError(
            f"Insufficient credits for backend '{backend_name}'. "
            "Please top up your account.",
            details={"original_error": str(error)},
        )

    if any(keyword in error_message for keyword in ["quota", "limit exceeded", "rate limit"]):
        return QuotaExceededError(
            f"Quota exceeded for backend '{backend_name}'. "
            "Please try again later or upgrade your plan.",
            details={"original_error": str(error)},
        )

    # Check for network errors
    if any(keyword in error_message for keyword in ["connection", "timeout", "network", "dns", "refused"]):
        return NetworkError(
            f"Network error while communicating with backend '{backend_name}'.",
            details={"original_error": str(error)},
        )

    return error


# -----------------------------------------------------------------------------
# Task Submission
# -----------------------------------------------------------------------------

def submit_task(
    circuit: "Circuit",
    backend: str,
    shots: int = 1000,
    metadata: dict | None = None,
    dummy: bool | None = None,
    **kwargs: Any,
) -> str:
    """Submit a single circuit to a quantum backend.

    This function converts the circuit to the backend's native format,
    submits it, and caches the task information locally.

    Args:
        circuit: The UnifiedQuantum Circuit to submit.
        backend: The backend name (e.g., 'originq', 'quafu', 'ibm').
        shots: Number of measurement shots.
        metadata: Optional metadata to store with the task.
        dummy: Override dummy mode. If None, uses UNIQC_DUMMY env var.
            When True, uses local simulation instead of real backend.
        **kwargs: Additional backend-specific parameters.
            - For Quafu: chip_id, auto_mapping
            - For OriginQ: backend_name (e.g., 'origin:wuyuan:d5'), circuit_optimize, measurement_amend

    Returns:
        The task ID assigned by the backend.

    Raises:
        BackendNotFoundError: If the backend is not recognized.
        BackendNotAvailableError: If the backend is not available.
        AuthenticationError: If authentication fails.
        InsufficientCreditsError: If account has insufficient credits.
        QuotaExceededError: If usage quota is exceeded.
        NetworkError: If a network error occurs.

    Example:
        >>> circuit = Circuit()
        >>> circuit.h(0)
        >>> circuit.measure(0)
        >>> task_id = submit_task(circuit, backend='originq', shots=1000, backend_name='origin:wuyuan:d5')
        >>> # Use dummy mode for local simulation
        >>> task_id = submit_task(circuit, backend='quafu', dummy=True)
    """
    # Determine if dummy mode should be used
    use_dummy = dummy if dummy is not None else UNIQC_DUMMY

    if use_dummy:
        # Use dummy adapter for local simulation
        return _submit_dummy(circuit, backend, shots, metadata, **kwargs)

    # Get backend instance
    try:
        backend_instance = backend_module.get_backend(backend)
    except ValueError as e:
        raise BackendNotFoundError(str(e)) from e

    # Check backend availability
    if not backend_instance.is_available():
        raise BackendNotAvailableError(
            f"Backend '{backend}' is not available. "
            "Please check your configuration and credentials."
        )

    # Convert circuit using adapter
    try:
        adapter = _get_adapter(backend)
        native_circuit = adapter.adapt(circuit)
    except Exception as e:
        raise _map_adapter_error(e, backend) from e

    # Submit to backend
    try:
        task_id = backend_instance.submit(native_circuit, shots=shots, **kwargs)
    except Exception as e:
        mapped_error = _map_adapter_error(e, backend)
        raise mapped_error from e

    # Create and save task info
    task_info = TaskInfo(
        task_id=task_id,
        backend=backend,
        status=TaskStatus.RUNNING,
        shots=shots,
        metadata=metadata or {},
    )
    save_task(task_info)

    return task_id


def _submit_dummy(
    circuit: "Circuit",
    backend: str,
    shots: int = 1000,
    metadata: dict | None = None,
    **kwargs: Any,
) -> str:
    """Submit a circuit using the dummy adapter for local simulation.

    Args:
        circuit: The UnifiedQuantum Circuit to simulate.
        backend: The backend name (used for logging/metadata only).
        shots: Number of measurement shots.
        metadata: Optional metadata.
        **kwargs: Additional parameters (passed to dummy adapter).

    Returns:
        Task ID from the dummy adapter.
    """
    from uniqc.task.adapters.dummy_adapter import DummyAdapter

    # Create dummy adapter
    dummy_adapter = DummyAdapter(
        noise_model=kwargs.get("noise_model"),
        available_qubits=kwargs.get("available_qubits"),
        available_topology=kwargs.get("available_topology"),
    )

    # Submit to dummy adapter
    originir = circuit.originir
    task_id = dummy_adapter.submit(originir, shots=shots)

    # Get result from dummy adapter
    result = dummy_adapter.query(task_id)
    adapter_status = result.get("status", TASK_STATUS_RUNNING)

    # Map adapter status to TaskStatus
    status_map = {
        TASK_STATUS_SUCCESS: TaskStatus.SUCCESS,
        TASK_STATUS_FAILED: TaskStatus.FAILED,
        TASK_STATUS_RUNNING: TaskStatus.RUNNING,
        "pending": TaskStatus.PENDING,
        "cancelled": TaskStatus.CANCELLED,
    }
    task_status = status_map.get(adapter_status, TaskStatus.FAILED)

    # Create and save task info
    task_info = TaskInfo(
        task_id=task_id,
        backend=f"dummy:{backend}",
        status=task_status,
        shots=shots,
        metadata=metadata or {},
    )

    # Store result if successful
    if adapter_status == TASK_STATUS_SUCCESS:
        task_info.result = result.get("result")

    save_task(task_info)

    return task_id


def submit_batch(
    circuits: list["Circuit"],
    backend: str,
    shots: int = 1000,
    dummy: bool | None = None,
    **kwargs: Any,
) -> list[str]:
    """Submit multiple circuits as a batch to a quantum backend.

    Args:
        circuits: List of UnifiedQuantum Circuits to submit.
        backend: The backend name.
        shots: Number of measurement shots per circuit.
        dummy: Override dummy mode. If None, uses UNIQC_DUMMY env var.
        **kwargs: Additional backend-specific parameters.
            - For Quafu: chip_id, auto_mapping, group_name
            - For OriginQ: backend_name (e.g., 'origin:wuyuan:d5'), circuit_optimize

    Returns:
        List of task IDs assigned by the backend.

    Raises:
        BackendNotFoundError: If the backend is not recognized.
        BackendNotAvailableError: If the backend is not available.
        AuthenticationError: If authentication fails.
        InsufficientCreditsError: If account has insufficient credits.
        QuotaExceededError: If usage quota is exceeded.
        NetworkError: If a network error occurs.

    Example:
        >>> circuits = [circuit1, circuit2, circuit3]
        >>> task_ids = submit_batch(circuits, backend='quafu', shots=1000, chip_id='ScQ-P10')
    """
    # Determine if dummy mode should be used
    use_dummy = dummy if dummy is not None else UNIQC_DUMMY

    if use_dummy:
        # Use dummy adapter for local simulation
        return _submit_batch_dummy(circuits, backend, shots, **kwargs)

    # Get backend instance
    try:
        backend_instance = backend_module.get_backend(backend)
    except ValueError as e:
        raise BackendNotFoundError(str(e)) from e

    # Check backend availability
    if not backend_instance.is_available():
        raise BackendNotAvailableError(
            f"Backend '{backend}' is not available. "
            "Please check your configuration and credentials."
        )

    # Convert circuits using adapter
    try:
        adapter = _get_adapter(backend)
        native_circuits = adapter.adapt_batch(circuits)
    except Exception as e:
        raise _map_adapter_error(e, backend) from e

    # Submit batch to backend
    try:
        result = backend_instance.submit_batch(native_circuits, shots=shots, **kwargs)
        # Handle both list of task IDs and single group ID
        if isinstance(result, list):
            task_ids = result
        else:
            task_ids = [result]
    except Exception as e:
        mapped_error = _map_adapter_error(e, backend)
        raise mapped_error from e

    # Create and save task info for each task
    for task_id in task_ids:
        task_info = TaskInfo(
            task_id=task_id,
            backend=backend,
            status=TaskStatus.RUNNING,
            shots=shots,
            metadata={"batch": True, "batch_size": len(circuits)},
        )
        save_task(task_info)

    return task_ids


def _submit_batch_dummy(
    circuits: list["Circuit"],
    backend: str,
    shots: int = 1000,
    **kwargs: Any,
) -> list[str]:
    """Submit multiple circuits using the dummy adapter.

    Args:
        circuits: List of UnifiedQuantum Circuits to simulate.
        backend: The backend name (used for logging/metadata only).
        shots: Number of measurement shots per circuit.
        **kwargs: Additional parameters.

    Returns:
        List of task IDs from the dummy adapter.
    """
    from uniqc.task.adapters.dummy_adapter import DummyAdapter

    # Create dummy adapter
    dummy_adapter = DummyAdapter(
        noise_model=kwargs.get("noise_model"),
        available_qubits=kwargs.get("available_qubits"),
        available_topology=kwargs.get("available_topology"),
    )

    # Submit all circuits
    originir_circuits = [c.originir for c in circuits]
    task_ids = dummy_adapter.submit_batch(originir_circuits, shots=shots)

    # Create and save task info for each
    for task_id in task_ids:
        result = dummy_adapter.query(task_id)
        adapter_status = result.get("status", TASK_STATUS_RUNNING)

        # Map adapter status to TaskStatus
        status_map = {
            TASK_STATUS_SUCCESS: TaskStatus.SUCCESS,
            TASK_STATUS_FAILED: TaskStatus.FAILED,
            TASK_STATUS_RUNNING: TaskStatus.RUNNING,
        }
        task_status = status_map.get(adapter_status, TaskStatus.FAILED)

        task_info = TaskInfo(
            task_id=task_id,
            backend=f"dummy:{backend}",
            status=task_status,
            shots=shots,
            metadata={"batch": True, "batch_size": len(circuits)},
        )
        if adapter_status == TASK_STATUS_SUCCESS:
            task_info.result = result.get("result")
        save_task(task_info)

    return task_ids


# -----------------------------------------------------------------------------
# Task Query
# -----------------------------------------------------------------------------

def query_task(task_id: str, backend: str | None = None) -> TaskInfo:
    """Query the status of a task.

    This function queries the backend for the current status of a task
    and updates the local cache.

    Args:
        task_id: The task identifier.
        backend: The backend name. If None, attempts to look up from cache.
            Prefer using None to let the system auto-detect the correct backend.

    Returns:
        TaskInfo with current status and result if available.

    Raises:
        TaskNotFoundError: If the task is not found locally or remotely.
        BackendNotFoundError: If the backend is not recognized.
        NetworkError: If a network error occurs.

    Example:
        >>> info = query_task('task-123', backend='quafu')
        >>> print(info.status)
        'success'
    """
    # Always prefer cached backend info to handle dummy mode correctly
    cached_task = get_task(task_id)
    if cached_task is not None:
        # Use cached backend (e.g., 'dummy:originq' for dummy mode)
        backend = cached_task.backend
        # For dummy tasks, results are already stored - return cached info directly
        if backend.startswith("dummy:"):
            return cached_task

    if backend is None:
        raise TaskNotFoundError(
            f"Task '{task_id}' not found in local cache. "
            "Please provide the backend parameter."
        )

    # Get backend instance (strip 'dummy:' prefix if present)
    actual_backend = backend.split(":", 1)[-1] if backend.startswith("dummy:") else backend
    try:
        backend_instance = backend_module.get_backend(actual_backend)
    except ValueError as e:
        raise BackendNotFoundError(str(e)) from e

    # Query backend
    try:
        result = backend_instance.query(task_id)
    except Exception as e:
        mapped_error = _map_adapter_error(e, backend)
        if isinstance(mapped_error, NetworkError):
            raise mapped_error from e
        # For other errors, try to use cached info
        cached_task = get_task(task_id)
        if cached_task is not None:
            return cached_task
        raise TaskNotFoundError(
            f"Task '{task_id}' not found: {e}",
            task_id=task_id,
        ) from e

    # Map adapter status to TaskStatus
    adapter_status = result.get("status", TASK_STATUS_RUNNING)
    status_map = {
        TASK_STATUS_SUCCESS: TaskStatus.SUCCESS,
        TASK_STATUS_FAILED: TaskStatus.FAILED,
        TASK_STATUS_RUNNING: TaskStatus.RUNNING,
        "pending": TaskStatus.PENDING,
        "cancelled": TaskStatus.CANCELLED,
    }
    task_status = status_map.get(adapter_status, TaskStatus.PENDING)

    # Update task info
    task_info = TaskInfo(
        task_id=task_id,
        backend=backend,
        status=task_status,
        result=result.get("result") if task_status == TaskStatus.SUCCESS else None,
    )

    # Merge with existing metadata if available
    cached_task = get_task(task_id)
    if cached_task is not None:
        task_info.submit_time = cached_task.submit_time
        task_info.shots = cached_task.shots
        task_info.metadata = cached_task.metadata

    save_task(task_info)
    return task_info


def wait_for_result(
    task_id: str,
    backend: str | None = None,
    timeout: float = 300.0,
    poll_interval: float = 5.0,
    raise_on_failure: bool = True,
) -> dict | None:
    """Wait for a task to complete and return its result.

    This function polls the task status until it completes, fails, or
    the timeout is reached.

    Args:
        task_id: The task identifier.
        backend: The backend name. If None, attempts to look up from cache.
        timeout: Maximum time to wait in seconds.
        poll_interval: Time between status checks in seconds.
        raise_on_failure: If True, raises TaskFailedError on task failure.

    Returns:
        The task result dictionary if successful, None if timed out.

    Raises:
        TaskTimeoutError: If the timeout is reached before completion.
        TaskFailedError: If the task fails and raise_on_failure is True.
        TaskNotFoundError: If the task is not found.
        NetworkError: If a network error occurs.

    Example:
        >>> result = wait_for_result('task-123', backend='quafu', timeout=300)
        >>> print(result['counts'])
        {'00': 512, '11': 488}
    """
    start_time = time.time()

    while True:
        # Query current status
        task_info = query_task(task_id, backend)

        # Check if completed
        if task_info.status == TaskStatus.SUCCESS:
            # Unwrap: adapter returns {"result": counts_dict}, return just the counts
            raw = task_info.result
            if isinstance(raw, dict) and "result" in raw:
                return raw["result"]
            return raw

        # Check if failed
        if task_info.status == TaskStatus.FAILED:
            if raise_on_failure:
                raise TaskFailedError(
                    f"Task '{task_id}' failed on backend '{task_info.backend}'.",
                    task_id=task_id,
                    backend=task_info.backend,
                )
            return None

        # Check timeout — but first do a final non-cached query so we
        # don't raise TaskTimeoutError for a task that actually failed.
        elapsed = time.time() - start_time
        if elapsed >= timeout:
            # One last query without cache to get the true cloud status.
            try:
                final_info = backend_module.get_backend(backend).query(task_id)
            except Exception:
                pass  # fall through to timeout error
            else:
                if final_info.get("status") == TASK_STATUS_FAILED:
                    raise TaskFailedError(
                        f"Task '{task_id}' failed on backend '{backend}'.",
                        task_id=task_id,
                        backend=backend,
                    )
                if final_info.get("status") == TASK_STATUS_SUCCESS:
                    return final_info.get("result")

            raise TaskTimeoutError(
                f"Timeout waiting for task '{task_id}' to complete.",
                task_id=task_id,
                timeout=timeout,
            )

        # Wait before next poll
        time.sleep(poll_interval)


# -----------------------------------------------------------------------------
# TaskManager Class
# -----------------------------------------------------------------------------

class TaskManager:
    """High-level task manager for quantum computing workflows.

    This class provides a convenient interface for managing quantum tasks
    with persistent caching and batch operations.

    Example:
        >>> manager = TaskManager()
        >>> task_id = manager.submit(circuit, backend='quafu', shots=1000)
        >>> result = manager.wait_for_result(task_id)
        >>> print(result)
    """

    def __init__(self, cache_dir: Path | str | None = None) -> None:
        """Initialize the TaskManager.

        Args:
            cache_dir: Optional custom cache directory.
        """
        self._cache_dir = Path(cache_dir) if cache_dir else None

    def submit(
        self,
        circuit: "Circuit",
        backend: str,
        shots: int = 1000,
        metadata: dict | None = None,
        **kwargs: Any,
    ) -> str:
        """Submit a single circuit."""
        return submit_task(
            circuit,
            backend,
            shots=shots,
            metadata=metadata,
            **kwargs,
        )

    def submit_batch(
        self,
        circuits: list["Circuit"],
        backend: str,
        shots: int = 1000,
        **kwargs: Any,
    ) -> list[str]:
        """Submit multiple circuits as a batch."""
        return submit_batch(
            circuits,
            backend,
            shots=shots,
            **kwargs,
        )

    def query(self, task_id: str, backend: str | None = None) -> TaskInfo:
        """Query a task's status."""
        return query_task(task_id, backend)

    def wait_for_result(
        self,
        task_id: str,
        backend: str | None = None,
        timeout: float = 300.0,
        poll_interval: float = 5.0,
        raise_on_failure: bool = True,
    ) -> dict | None:
        """Wait for a task to complete."""
        return wait_for_result(
            task_id,
            backend,
            timeout=timeout,
            poll_interval=poll_interval,
            raise_on_failure=raise_on_failure,
        )

    def list_tasks(
        self,
        status: str | None = None,
        backend: str | None = None,
    ) -> list[TaskInfo]:
        """List tasks from cache."""
        return list_tasks(status, backend, cache_dir=self._cache_dir)

    def clear_completed(self) -> int:
        """Clear completed tasks from cache."""
        return clear_completed_tasks(cache_dir=self._cache_dir)

    def clear_cache(self) -> None:
        """Clear all tasks from cache."""
        clear_cache(cache_dir=self._cache_dir)
