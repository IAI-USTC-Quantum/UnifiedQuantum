"""Task management with local caching for quantum computing backends.

This module provides a unified interface for submitting quantum tasks,
managing task lifecycle, and caching results locally. All persistent
storage is delegated to :class:`uniqc.backend_adapter.task.store.TaskStore` (SQLite at
``~/.uniqc/cache/tasks.sqlite``).

Usage::

    from uniqc.backend_adapter.task_manager import submit_task, query_task, wait_for_result, dry_run_task
    from uniqc.circuit_builder import Circuit

    # Create a circuit
    circuit = Circuit()
    circuit.h(0)
    circuit.cnot(0, 1)
    circuit.measure(0, 1)

    # Dry-run: validate circuit offline before submitting
    result = dry_run_task(circuit, backend='quafu', shots=1000, chip_id='ScQ-P18')
    if not result.success:
        print(f"Validation failed: {result.error}")

    # Submit task
    task_id = submit_task(circuit, backend='quafu', shots=1000)

    # Wait for result
    result = wait_for_result(task_id, backend='quafu', timeout=300)

    # Query task status
    info = query_task(task_id, backend='quafu')
    print(info['status'])  # 'running', 'success', or 'failed'

    # Use dummy backend for local simulation
    task_id = submit_task(circuit, backend='dummy', shots=1000)

Note:
    Any dry-run success followed by actual submission failure is a critical bug.
    Please report it at the UnifiedQuantum issue tracker.
"""

from __future__ import annotations

__all__ = [
    # Task submission
    "submit_task",
    "submit_batch",
    # Dry-run
    "dry_run_task",
    "dry_run_batch",
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
    # Storage path (useful for tests / tooling)
    "DEFAULT_CACHE_DIR",
]

import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from uniqc.circuit_builder.qcircuit import Circuit

from uniqc.backend_adapter import backend as backend_module
from uniqc.backend_adapter.circuit_adapter import (
    CircuitAdapter,
    IBMCircuitAdapter,
    OriginQCircuitAdapter,
    QuafuCircuitAdapter,
    QuarkCircuitAdapter,
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
from uniqc.backend_adapter.task.adapters.base import (
    TASK_STATUS_FAILED,
    TASK_STATUS_RUNNING,
    TASK_STATUS_SUCCESS,
    QuantumAdapter,
)
from uniqc.backend_adapter.task.options import BackendOptions, BackendOptionsFactory
from uniqc.backend_adapter.task.result_types import DryRunResult, UnifiedResult
from uniqc.backend_adapter.task.store import (
    DEFAULT_CACHE_DIR,
    TaskInfo,
    TaskStatus,
    TaskStore,
)

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Circuit Adapter Mapping
# -----------------------------------------------------------------------------

ADAPTER_MAP: dict[str, type[CircuitAdapter]] = {
    "originq": OriginQCircuitAdapter,
    "quafu": QuafuCircuitAdapter,
    "quark": QuarkCircuitAdapter,
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
        raise BackendNotFoundError(f"No circuit adapter for backend '{backend_name}'. Available adapters: {available}")
    return ADAPTER_MAP[backend_name]()


# -----------------------------------------------------------------------------
# Dry-run validation
# -----------------------------------------------------------------------------


def dry_run_task(
    circuit: Circuit,
    backend: str,
    shots: int = 1000,
    **kwargs: Any,
) -> DryRunResult:
    """Validate a circuit against a backend without making network calls.

    This performs a dry-run validation that checks:
    1. The circuit can be successfully translated to the platform's native format.
    2. The resulting native circuit object is structurally valid.
    3. The qubit count fits within the backend's limits (where determinable offline).
    4. Gate basis compatibility is confirmed (where determinable offline).

    This function makes NO cloud API calls.

    Args:
        circuit: The UnifiedQuantum Circuit to validate.
        backend: The backend name (e.g., 'originq', 'quafu', 'quark', 'ibm',
            'dummy', 'dummy:originq:WK_C180').
        shots: Number of measurement shots for validation.
        **kwargs: Additional backend-specific parameters.
            - For IBM: chip_id (required for full validation)
            - For Quafu: chip_id (required for full validation)
            - For OriginQ: backend_name (e.g., 'origin:wuyuan:d5')

    Returns:
        DryRunResult indicating success or failure with details and warnings.

    Example:
        >>> from uniqc.circuit_builder import Circuit
        >>> circuit = Circuit()
        >>> circuit.h(0)
        >>> circuit.measure(0)
        >>> result = dry_run_task(circuit, backend='quafu', shots=1000, chip_id='ScQ-P18')
        >>> if result.success:
        ...     print("Circuit is valid for submission")
        >>> else:
        ...     print(f"Validation failed: {result.error}")

    Note:
        Any dry-run success followed by actual submission failure is a
        critical bug. Please report it at the UnifiedQuantum issue tracker.
    """
    from uniqc.backend_adapter.task.adapters.dummy_adapter import DummyAdapter
    from uniqc.backend_adapter.task.adapters.originq_adapter import OriginQAdapter
    from uniqc.backend_adapter.task.adapters.qiskit_adapter import QiskitAdapter
    from uniqc.backend_adapter.task.adapters.quafu_adapter import QuafuAdapter
    from uniqc.backend_adapter.task.adapters.quark_adapter import QuarkAdapter

    adapter_map: dict[str, type[QuantumAdapter]] = {
        "originq": OriginQAdapter,
        "quafu": QuafuAdapter,
        "quark": QuarkAdapter,
        "ibm": QiskitAdapter,
        "dummy": DummyAdapter,
    }

    if backend == "dummy" or backend.startswith("dummy:"):
        try:
            from uniqc.backend_adapter.dummy_backend import dummy_adapter_kwargs

            adapter: QuantumAdapter = DummyAdapter(
                **dummy_adapter_kwargs(
                    dummy_backend,
                    chip_characterization=kwargs.get("chip_characterization"),
                    noise_model=kwargs.get("noise_model"),
                    available_qubits=kwargs.get("available_qubits"),
                    available_topology=kwargs.get("available_topology"),
                )
            )
        except Exception as e:
            return DryRunResult(
                success=False,
                details=f"Cannot initialize dummy adapter: {e}",
                error=str(e),
                backend_name="dummy",
            )
    else:
        if backend not in adapter_map:
            return DryRunResult(
                success=False,
                details=f"No adapter registered for backend '{backend}'.",
                error=f"Unknown backend: {backend}",
                warnings=("Known backends: originq, quafu, quark, ibm",),
            )

        try:
            adapter = adapter_map[backend]()
        except Exception as e:
            return DryRunResult(
                success=False,
                details=f"Failed to initialize adapter for '{backend}': {e}",
                error=str(e),
            )

    originir = circuit.originir
    try:
        return adapter.dry_run(originir, shots=shots, **kwargs)
    except Exception as e:
        return DryRunResult(
            success=False,
            details=f"dry_run() raised an unhandled exception: {e}",
            error=str(e),
            backend_name=getattr(adapter, "name", None),
        )


def dry_run_batch(
    circuits: list[Circuit],
    backend: str,
    shots: int = 1000,
    **kwargs: Any,
) -> list[DryRunResult]:
    """Validate multiple circuits against a backend without making network calls.

    Runs dry_run_task() on each circuit in sequence and returns a list of
    results, one per circuit in input order.

    Args:
        circuits: List of UnifiedQuantum Circuits to validate.
        backend: The backend name.
        shots: Number of measurement shots per circuit.
        **kwargs: Additional backend-specific parameters.

    Returns:
        List of DryRunResult, one per circuit in input order.

    Note:
        Any dry-run success followed by actual submission failure is a
        critical bug. Please report it at the UnifiedQuantum issue tracker.
    """
    return [dry_run_task(c, backend, shots=shots, **kwargs) for c in circuits]


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
    try:
        return _store(cache_dir).get(task_id)
    except OSError:
        return None
    except Exception as exc:
        if exc.__class__.__module__ == "sqlite3":
            return None
        raise


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


def clear_completed_tasks(
    cache_dir: Path | None = None, status: str | None = None
) -> int:
    """Remove completed tasks from the cache.

    Args:
        cache_dir: Optional custom cache directory.
        status: If given, only remove tasks with this status (case-insensitive,
            same normalization as ``list_tasks``). When ``None``, removes all
            tasks in any terminal status (success, failed, cancelled, ...).

    Returns:
        Number of tasks removed.
    """
    if status is None:
        return _store(cache_dir).clear_completed()
    return _store(cache_dir).clear_completed(terminal_statuses=(status,))


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
            f"Authentication failed for backend '{backend_name}'. Please check your API token or credentials.",
            details={"original_error": str(error)},
        )

    # Check for credit/quota errors
    if any(keyword in error_message for keyword in ["credit", "balance", "payment", "billing"]):
        return InsufficientCreditsError(
            f"Insufficient credits for backend '{backend_name}'. Please top up your account.",
            details={"original_error": str(error)},
        )

    if any(keyword in error_message for keyword in ["quota", "limit exceeded", "rate limit"]):
        return QuotaExceededError(
            f"Quota exceeded for backend '{backend_name}'. Please try again later or upgrade your plan.",
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


def _metadata_with_circuit(circuit: Circuit, metadata: dict | None) -> dict:
    """Return task metadata enriched with the submitted circuit IR."""
    enriched = dict(metadata or {})
    enriched.setdefault("circuit_ir", circuit.originir)
    enriched.setdefault("circuit_language", "OriginIR")
    return enriched


def _resolve_backend_info_for_validation(backend: str, kwargs: dict[str, Any]):
    """Best-effort lookup of a fresh BackendInfo for ``backend``.

    Returns ``None`` when nothing is known offline (caller will skip the
    topology / gate-set checks with a warning rather than fail closed).
    The lookup is cache-only — we never make a live cloud call here, both
    because submission paths must stay synchronous-fast and because the
    caller may have authentication issues we should surface elsewhere.

    Honours the per-call hint ``kwargs['backend_info']`` if the caller
    already resolved it.
    """
    explicit = kwargs.get("backend_info")
    if explicit is not None:
        return explicit
    if backend in ("dummy",) or backend.startswith("dummy:"):
        return None
    try:
        from uniqc.backend_adapter.backend_cache import get_cached_backends, is_stale
        from uniqc.backend_adapter.backend_info import Platform, parse_backend_id

        platform, name = parse_backend_id(backend)
    except Exception:
        return None
    if platform == Platform.DUMMY:
        return None
    try:
        cached = get_cached_backends(platform)
    except Exception:
        return None
    fresh = not is_stale(platform.value)
    for entry in cached:
        if entry.name == name:
            # Annotate freshness in extra so callers / reports can react.
            if not fresh:
                # Frozen dataclass; ship a copy with a warning marker.
                import dataclasses

                extra = dict(entry.extra)
                extra.setdefault("_uniqc_topology_stale", True)
                return dataclasses.replace(entry, extra=extra)
            return entry
    return None


def _prepare_circuit_for_submission(
    circuit: Circuit,
    backend: str,
    kwargs: dict[str, Any],
    *,
    auto_compile: bool = True,
) -> tuple[Circuit, dict[str, Any]]:
    """Validate a circuit against ``backend`` and optionally compile it.

    Returns ``(circuit, metadata_extras)``. The returned circuit is either the
    original (when it already satisfies the backend's gate set / topology) or
    a freshly-compiled circuit produced by
    :func:`uniqc.compile.compile_for_backend`.

    Raises :class:`uniqc.exceptions.UnsupportedGateError` when validation fails
    and the circuit cannot be auto-compiled (or auto-compilation also fails to
    land in the basis set / topology).

    Validation is split into two layers:

    1. **Hard block** (never skippable): IR language compatibility — gates that
       cannot be expressed in the target platform's submission format (e.g.
       ``RPhi`` → QASM2-only platforms) are always rejected.
    2. **Soft validation** (skippable): basis gate set, qubit count, topology.
       Pass ``kwargs['skip_validation']=True`` to bypass these checks and let
       the cloud platform handle them.
    """
    skip_validation = kwargs.pop("skip_validation", False)

    if backend == "dummy" or backend.startswith("dummy:"):
        # Dummy backends accept anything; their dedicated path handles compilation.
        return circuit, {}

    from uniqc.compile.policy import compile_for_backend, resolve_basis_gates, resolve_submit_language
    from uniqc.compile.validation import compatibility_report

    language = resolve_submit_language(backend)

    # --- Hard block: IR language compatibility (never skippable) ---
    # Gates like RPhi/RPHI90/PHASE2Q/UU15 cannot be expressed in QASM2;
    # submitting them to QASM2-only platforms (Quafu/Quark/IBM) will always
    # fail at the cloud backend.
    _lang_report = compatibility_report(circuit, backend_info=None, language=language)
    if _lang_report.errors:
        from uniqc.exceptions import UnsupportedGateError

        raise UnsupportedGateError("; ".join(_lang_report.errors))

    if skip_validation:
        return circuit, {}

    # --- Soft validation: basis gates, qubit count, topology ---
    backend_info = _resolve_backend_info_for_validation(backend, kwargs)
    basis = list(resolve_basis_gates(backend, backend_info)) or None

    extras: dict[str, Any] = {}
    report = compatibility_report(
        circuit,
        backend_info,
        basis_gates=basis,
        language=language,
    )
    extras["validation_passed"] = bool(report.compatible)
    extras["validation_warnings"] = list(report.warnings)
    extras["gate_depth"] = report.gate_depth
    extras["used_gates"] = sorted(report.used_gates)
    extras["submit_language"] = language

    if backend_info is not None and backend_info.extra.get("_uniqc_topology_stale"):
        extras["topology_stale"] = True
        extras["validation_warnings"].append(
            f"Backend topology cache for {backend} is stale (older than TTL); "
            "consider running `uniqc backend update`."
        )

    if report.compatible:
        return circuit, extras

    if not auto_compile or backend_info is None:
        from uniqc.exceptions import UnsupportedGateError

        msg = "; ".join(report.errors) or "validation failed"
        raise UnsupportedGateError(
            f"Circuit is not compatible with backend '{backend}': {msg}. "
            "Use skip_validation=True to bypass."
        )

    # Try compiling and re-validate.
    try:
        compiled = compile_for_backend(circuit, backend_info)
    except Exception as exc:  # pragma: no cover - depends on optional qiskit
        from uniqc.exceptions import UnsupportedGateError

        raise UnsupportedGateError(
            f"Circuit failed validation for '{backend}' and auto-compile errored: {exc}"
        ) from exc

    post = compatibility_report(
        compiled,
        backend_info,
        basis_gates=basis,
        language=language,
    )
    extras["compiled"] = True
    extras["compiled_gate_depth"] = post.gate_depth
    extras["compiled_used_gates"] = sorted(post.used_gates)
    extras["compiled_circuit_ir"] = compiled.originir if hasattr(compiled, "originir") else str(compiled)
    extras["compiled_circuit_language"] = "OriginIR"
    if not post.compatible:
        from uniqc.exceptions import UnsupportedGateError

        msg = "; ".join(post.errors)
        raise UnsupportedGateError(
            f"Auto-compile for '{backend}' did not land in the backend basis/topology: {msg}"
        )
    return compiled, extras


def _backend_platform_key(backend: str) -> str:
    return backend.split(":", 1)[0]


def _backend_info_from_chip(spec: Any):
    """Build BackendInfo for compiling a chip-backed dummy target."""
    from uniqc.backend_adapter.backend_info import BackendInfo, QubitTopology

    chip = spec.chip_characterization
    if chip is None or spec.source_platform is None or spec.source_name is None:
        return None
    return BackendInfo(
        platform=spec.source_platform,
        name=spec.source_name,
        description=f"Compile target for {spec.identifier}",
        num_qubits=len(getattr(chip, "available_qubits", ())),
        topology=tuple(QubitTopology(u=int(e.u), v=int(e.v)) for e in getattr(chip, "connectivity", ())),
        status="available",
        is_simulator=False,
        is_hardware=True,
    )


def _compile_for_chip_backed_dummy(circuit: Circuit, spec: Any, metadata: dict | None) -> tuple[str, dict]:
    """Compile source circuit when a dummy target mirrors a real chip."""
    enriched = dict(metadata or {})
    if spec.source_platform is None or spec.chip_characterization is None:
        return circuit.originir, enriched

    from uniqc.compile import compile as compile_circuit

    backend_info = _backend_info_from_chip(spec)
    compiled_originir = compile_circuit(
        circuit,
        backend_info=backend_info,
        chip_characterization=spec.chip_characterization,
        output_format="originir",
    )
    enriched.setdefault("compiled_circuit_ir", compiled_originir)
    enriched.setdefault("compiled_circuit_language", "OriginIR")
    enriched.setdefault("executed_circuit_ir", compiled_originir)
    enriched.setdefault("executed_circuit_language", "OriginIR")
    enriched.setdefault("compile_target_backend", f"{spec.source_platform.value}:{spec.source_name}")
    return compiled_originir, enriched


def submit_task(
    circuit: Circuit,
    backend: str,
    shots: int = 1000,
    metadata: dict | None = None,
    options: BackendOptions | dict | None = None,
    **kwargs: Any,
) -> str:
    """Submit a single circuit to a quantum backend.

    This function converts the circuit to the backend's native format,
    submits it, and caches the task information locally.

    Args:
        circuit: The UnifiedQuantum Circuit to submit.
        backend: The backend name (e.g., 'originq', 'quafu', 'ibm', 'dummy',
            'dummy:originq:WK_C180').
        shots: Number of measurement shots.
        metadata: Optional metadata to store with the task.
        options: Optional typed backend options. Accepts a
            :class:`BackendOptions` instance, a plain dict (treated as
            ``**kwargs``), or ``None`` for platform defaults.
            Example::

                from uniqc.backend_adapter.task.options import OriginQOptions
                opts = OriginQOptions(circuit_optimize=False)
                submit_task(circuit, "originq", options=opts)

            If provided alongside ``**kwargs``, ``options`` takes precedence
            for the fields it defines.
        **kwargs: Additional backend-specific parameters.
            - For Quafu: chip_id, auto_mapping
            - For OriginQ: backend_name (e.g., 'origin:wuyuan:d5'), circuit_optimize, measurement_amend
            - For dummy: chip_characterization, noise_model, available_qubits, available_topology

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
        >>> # Local noisy simulation using chip characterization
        >>> from uniqc.backend_adapter.task.adapters.originq_adapter import OriginQAdapter
        >>> chip = OriginQAdapter().get_chip_characterization("origin:wuyuan:d5")
        >>> task_id = submit_task(circuit, backend='dummy', chip_characterization=chip)
    """
    import warnings

    # Normalise options
    if options is not None:
        opts = BackendOptionsFactory.normalize_options(options, _backend_platform_key(backend))
        merged_kwargs = opts.to_kwargs()
        merged_kwargs.update(kwargs)
        kwargs = merged_kwargs
        shots = opts.shots

    metadata = _metadata_with_circuit(circuit, metadata)

    # Route dummy backend through _submit_dummy which pre-populates the result.
    # This ensures 'uniqc result <task_id>' returns data immediately without
    # needing a subsequent query against a cloud backend.
    if backend == "dummy" or backend.startswith("dummy:"):
        return _submit_dummy(circuit, backend, shots=shots, metadata=metadata, **kwargs)

    # Pre-submission validation + optional auto-compile.
    auto_compile = kwargs.pop("auto_compile", True)
    circuit, prep_extras = _prepare_circuit_for_submission(
        circuit, backend, kwargs, auto_compile=auto_compile
    )
    metadata = {**metadata, **prep_extras}

    # Resolve backend instance
    try:
        backend_instance = backend_module.get_backend(backend)
    except ValueError as e:
        raise BackendNotFoundError(str(e)) from e

    # Check backend availability
    if not backend_instance.is_available():
        raise BackendNotAvailableError(
            f"Backend '{backend}' is not available. Please check your configuration and credentials."
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
    circuit: Circuit,
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
    from uniqc.backend_adapter.dummy_backend import dummy_adapter_kwargs, resolve_dummy_backend
    from uniqc.backend_adapter.task.adapters.dummy_adapter import DummyAdapter

    spec = resolve_dummy_backend(
        backend,
        chip_characterization=kwargs.get("chip_characterization"),
        noise_model=kwargs.get("noise_model"),
        available_qubits=kwargs.get("available_qubits"),
        available_topology=kwargs.get("available_topology"),
    )
    adapter_kwargs = dummy_adapter_kwargs(
        spec.identifier,
        chip_characterization=spec.chip_characterization,
        noise_model=kwargs.get("noise_model"),
        available_qubits=spec.available_qubits,
        available_topology=spec.available_topology,
    )
    dummy_adapter = DummyAdapter(**adapter_kwargs)

    originir, metadata = _compile_for_chip_backed_dummy(circuit, spec, metadata)
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
        backend=spec.identifier,
        status=task_status,
        shots=shots,
        metadata={
            **(metadata or {}),
            "dummy_backend_id": spec.identifier,
            "dummy_noise_source": spec.noise_source,
            "dummy_source_backend": (
                f"{spec.source_platform.value}:{spec.source_name}"
                if spec.source_platform is not None and spec.source_name
                else None
            ),
        },
    )

    # Store result if successful
    if adapter_status == TASK_STATUS_SUCCESS:
        task_info.result = result.get("result")

    save_task(task_info)

    return task_id


def submit_batch(
    circuits: list[Circuit],
    backend: str,
    shots: int = 1000,
    options: BackendOptions | dict | None = None,
    **kwargs: Any,
) -> list[str]:
    """Submit multiple circuits as a batch to a quantum backend.

    Args:
        circuits: List of UnifiedQuantum Circuits to submit.
        backend: The backend name.
        shots: Number of measurement shots per circuit.
        options: Optional typed backend options. Same as in :func:`submit_task`.
        **kwargs: Additional backend-specific parameters.
            - For Quafu: chip_id, auto_mapping, group_name
            - For OriginQ: backend_name (e.g., 'origin:wuyuan:d5'), circuit_optimize
            - For dummy: chip_characterization, noise_model, available_qubits

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
    # Normalise options
    if options is not None:
        opts = BackendOptionsFactory.normalize_options(options, _backend_platform_key(backend))
        merged_kwargs = opts.to_kwargs()
        merged_kwargs.update(kwargs)
        kwargs = merged_kwargs
        shots = opts.shots

    # Route dummy backend to _submit_batch_dummy which pre-populates results.
    if backend == "dummy" or backend.startswith("dummy:"):
        return _submit_batch_dummy(circuits, backend, shots=shots, **kwargs)

    # Pre-submission validation for each circuit; auto-compile any that fail.
    auto_compile = kwargs.pop("auto_compile", True)
    prepared: list[Circuit] = []
    prep_extras_list: list[dict[str, Any]] = []
    for c in circuits:
        c2, extras = _prepare_circuit_for_submission(
            c, backend, kwargs, auto_compile=auto_compile
        )
        prepared.append(c2)
        prep_extras_list.append(extras)
    circuits = prepared

    # Resolve backend instance
    try:
        backend_instance = backend_module.get_backend(backend)
    except ValueError as e:
        raise BackendNotFoundError(str(e)) from e

    # Check backend availability
    if not backend_instance.is_available():
        raise BackendNotAvailableError(
            f"Backend '{backend}' is not available. Please check your configuration and credentials."
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
        task_ids = result if isinstance(result, list) else [result]
    except Exception as e:
        mapped_error = _map_adapter_error(e, backend)
        raise mapped_error from e

    # Create and save task info for each task
    for index, task_id in enumerate(task_ids):
        metadata = {"batch": True, "batch_size": len(circuits)}
        if index < len(circuits):
            metadata = _metadata_with_circuit(circuits[index], metadata)
            if index < len(prep_extras_list):
                metadata.update(prep_extras_list[index])
        else:
            metadata["circuits"] = [
                _metadata_with_circuit(circuit, {})["circuit_ir"]
                for circuit in circuits
            ]
            metadata["circuit_language"] = "OriginIR"
        task_info = TaskInfo(
            task_id=task_id,
            backend=backend,
            status=TaskStatus.RUNNING,
            shots=shots,
            metadata=metadata,
        )
        save_task(task_info)

    return task_ids


def _submit_batch_dummy(
    circuits: list[Circuit],
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
    from uniqc.backend_adapter.dummy_backend import dummy_adapter_kwargs, resolve_dummy_backend
    from uniqc.backend_adapter.task.adapters.dummy_adapter import DummyAdapter

    spec = resolve_dummy_backend(
        backend,
        chip_characterization=kwargs.get("chip_characterization"),
        noise_model=kwargs.get("noise_model"),
        available_qubits=kwargs.get("available_qubits"),
        available_topology=kwargs.get("available_topology"),
    )
    adapter_kwargs = dummy_adapter_kwargs(
        spec.identifier,
        chip_characterization=spec.chip_characterization,
        noise_model=kwargs.get("noise_model"),
        available_qubits=spec.available_qubits,
        available_topology=spec.available_topology,
    )
    dummy_adapter = DummyAdapter(**adapter_kwargs)

    originir_circuits: list[str] = []
    compiled_metadata: list[dict] = []
    for circuit in circuits:
        originir, item_metadata = _compile_for_chip_backed_dummy(circuit, spec, {})
        originir_circuits.append(originir)
        compiled_metadata.append(item_metadata)
    task_ids = dummy_adapter.submit_batch(originir_circuits, shots=shots)

    # Create and save task info for each
    for index, task_id in enumerate(task_ids):
        result = dummy_adapter.query(task_id)
        adapter_status = result.get("status", TASK_STATUS_RUNNING)

        # Map adapter status to TaskStatus
        status_map = {
            TASK_STATUS_SUCCESS: TaskStatus.SUCCESS,
            TASK_STATUS_FAILED: TaskStatus.FAILED,
            TASK_STATUS_RUNNING: TaskStatus.RUNNING,
        }
        task_status = status_map.get(adapter_status, TaskStatus.FAILED)

        metadata = {"batch": True, "batch_size": len(circuits)}
        if index < len(circuits):
            metadata = _metadata_with_circuit(circuits[index], metadata)
            metadata.update(compiled_metadata[index])
        task_info = TaskInfo(
            task_id=task_id,
            backend=spec.identifier,
            status=task_status,
            shots=shots,
            metadata={
                **metadata,
                "dummy_backend_id": spec.identifier,
                "dummy_noise_source": spec.noise_source,
                "dummy_source_backend": (
                    f"{spec.source_platform.value}:{spec.source_name}"
                    if spec.source_platform is not None and spec.source_name
                    else None
                ),
            },
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
        if backend == "dummy" or backend.startswith("dummy:"):
            return cached_task

    if backend is None:
        raise TaskNotFoundError(f"Task '{task_id}' not found in local cache. Please provide the backend parameter.")

    # Get backend instance (strip 'dummy:' prefix if present)
    actual_backend = backend
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


def _wrap_as_unified_result(
    raw: Any,
    task_id: str,
    backend: str | None,
    shots: int | None = None,
) -> UnifiedResult:
    """Wrap a raw adapter result into a :class:`UnifiedResult`.

    Adapters historically return either a flat counts dict
    (``{"00": 512, "11": 488}``) or a wrapped form
    (``{"result": {"00": 512, ...}, ...}``). This helper normalizes both
    and preserves the original payload as ``raw_result``.
    """
    if isinstance(raw, UnifiedResult):
        return raw

    if isinstance(raw, dict) and "result" in raw and isinstance(raw["result"], dict):
        counts = raw["result"]
    elif isinstance(raw, dict):
        counts = raw
    else:
        counts = {}

    counts = {str(k): int(v) for k, v in counts.items()} if counts else {}

    backend_name = backend or "unknown"
    platform = backend_name.split(":", 1)[0] if backend_name else "unknown"

    result = UnifiedResult.from_counts(
        counts=counts,
        platform=platform,
        task_id=task_id,
        backend_name=backend_name,
        raw_result=raw,
    )
    if shots is not None and not result.shots:
        result.shots = shots
    return result


def wait_for_result(
    task_id: str,
    backend: str | None = None,
    timeout: float = 300.0,
    poll_interval: float = 5.0,
    raise_on_failure: bool = True,
) -> UnifiedResult | None:
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
        A :class:`UnifiedResult` on success, or ``None`` if the task failed
        and ``raise_on_failure=False``. The returned object is dict-like
        (``result["00"]``, ``len(result)``, iteration, equality with a plain
        counts dict all work). Use :meth:`UnifiedResult.raw` to access the
        original platform-specific payload.

    Raises:
        TaskTimeoutError: If the timeout is reached before completion.
        TaskFailedError: If the task fails and raise_on_failure is True.
        TaskNotFoundError: If the task is not found.
        NetworkError: If a network error occurs.

    Example:
        >>> result = wait_for_result('task-123', backend='quafu', timeout=300)
        >>> print(result.counts)        # unified accessor
        {'00': 512, '11': 488}
        >>> result['00']                # dict-like access still works
        512
        >>> result.raw()                # original adapter payload
        {'result': {'00': 512, '11': 488}, ...}
    """
    start_time = time.time()

    while True:
        # Query current status
        task_info = query_task(task_id, backend)

        # Check if completed
        if task_info.status == TaskStatus.SUCCESS:
            return _wrap_as_unified_result(
                task_info.result,
                task_id=task_id,
                backend=task_info.backend,
                shots=task_info.shots,
            )

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
                    return _wrap_as_unified_result(
                        final_info.get("result"),
                        task_id=task_id,
                        backend=backend,
                    )

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
        circuit: Circuit,
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
        circuits: list[Circuit],
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
    ) -> UnifiedResult | None:
        """Wait for a task to complete. See :func:`wait_for_result`."""
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
