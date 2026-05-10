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
    task_id = submit_task(circuit, backend='dummy:local:simulator', shots=1000)

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
    "poll_result",
    "get_result",
    "get_platform_task_ids",
    # Cache management
    "save_task",
    "get_task",
    "list_tasks",
    "clear_completed_tasks",
    "clear_cache",
    # Classes
    "TaskInfo",
    "TaskShard",
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
    TERMINAL_STATUSES,
    TaskInfo,
    TaskShard,
    TaskStatus,
    TaskStore,
    UNIQC_TASK_ID_PREFIX,
    generate_uniqc_task_id,
    is_uniqc_task_id,
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


def _normalize_circuit_input(circuit: Any) -> Circuit:
    """Auto-detect input type and convert to :class:`uniqc.Circuit`.

    Delegates to :func:`uniqc.circuit_builder.normalize.normalize_circuit_input`.
    """
    from uniqc.circuit_builder.normalize import normalize_circuit_input

    return normalize_circuit_input(circuit).circuit


def _get_adapter(backend_name: str) -> CircuitAdapter:
    """Get the appropriate circuit adapter for a backend.

    Accepts both bare platform ids (``"originq"``) and fully-qualified
    ``"provider:chip"`` ids (``"originq:WK_C180"``) — the chip suffix is
    stripped before looking up the adapter class.

    Args:
        backend_name: The platform name (e.g. ``'originq'``) or a
            ``'<platform>:<chip>'`` string.

    Returns:
        CircuitAdapter instance for the backend.

    Raises:
        BackendNotFoundError: If no adapter exists for the backend.
    """
    platform_key = backend_name.split(":", 1)[0] if ":" in backend_name else backend_name
    if platform_key not in ADAPTER_MAP:
        available = ", ".join(ADAPTER_MAP.keys())
        if ":" in backend_name:
            hint = (
                f" Did you mean `backend='{platform_key}', backend_name="
                f"'{backend_name.split(':', 1)[1]}'`?"
            )
        else:
            hint = ""
        raise BackendNotFoundError(
            f"No circuit adapter for backend '{backend_name}'. "
            f"Available adapters: {available}.{hint}"
        )
    return ADAPTER_MAP[platform_key]()


# Per-platform kwarg key used to identify the target chip / backend on the
# adapter. Used both for auto-injecting the chip from a "provider:chip"
# backend id, and for back-resolving the chip name when the user passes the
# legacy bare ``backend='originq'`` form together with a chip kwarg.
_PLATFORM_CHIP_KWARG: dict[str, str] = {
    "originq": "backend_name",
    "quafu": "chip_id",
    "quark": "chip_id",
    "ibm": "chip_id",
}


def _chip_from_kwargs(platform: str, kwargs: dict[str, Any]) -> str | None:
    """Return the chip id implied by ``kwargs`` for ``platform``, if any.

    Accepts the canonical key for the platform plus a few common aliases that
    appear in older docs/examples (``backend_name``/``chip_id``/``chip``).
    """
    for key in (_PLATFORM_CHIP_KWARG.get(platform, ""), "backend_name", "chip_id", "chip"):
        if not key:
            continue
        value = kwargs.get(key)
        if value:
            return str(value)
    return None


def _split_backend_id(backend: str) -> tuple[str, str | None]:
    """Split a backend id into ``(platform_key, chip_or_None)``.

    ``"dummy:..."`` is returned as platform-only — the dummy routing path
    handles its own sub-identifier parsing.
    """
    if backend.startswith("dummy:"):
        return "dummy", None
    if ":" in backend:
        platform, chip = backend.split(":", 1)
        chip = chip.strip()
        return platform.strip(), chip or None
    return backend.strip(), None


def _inject_chip_kwarg(platform: str, chip: str, kwargs: dict[str, Any]) -> None:
    """If the platform expects a chip kwarg and the caller didn't pass one,
    inject ``chip`` under the canonical key.

    User-supplied kwargs always win — we never overwrite an explicit value.
    """
    canonical_key = _PLATFORM_CHIP_KWARG.get(platform)
    if not canonical_key:
        return
    if _chip_from_kwargs(platform, kwargs) is not None:
        return
    kwargs[canonical_key] = chip


def _require_qualified_backend(backend: str, kwargs: dict[str, Any]) -> str:
    """Enforce the ``provider:chip`` backend format for cloud submissions.

    ``submit_task`` / ``submit_batch`` require a chip name in addition to a
    provider so that pre-submission validation can resolve the right
    ``BackendInfo`` (basis gates + topology). This helper accepts three forms
    and returns a normalised ``"platform:chip"`` id:

    * ``"provider:chip"``                 — used as-is
    * ``"provider"`` + ``chip_kwarg``     — combined into ``"provider:chip"``
      (legacy form that historic docs/tests use; kept for backward compat)
    * ``"provider"`` alone                — rejected with a helpful error that
      lists known chips from the local backend cache.

    ``dummy``/``dummy:*`` ids and unknown platforms are returned unchanged so
    that downstream code can produce its own error messages.
    """
    platform, chip = _split_backend_id(backend)

    # Dummy and unknown platforms: leave for downstream handlers.
    if platform == "dummy" or platform not in _PLATFORM_CHIP_KWARG:
        return backend

    if chip:
        # Already qualified — also mirror into kwargs so adapters that read
        # ``backend_name``/``chip_id`` see the same value.
        _inject_chip_kwarg(platform, chip, kwargs)
        return backend

    legacy_chip = _chip_from_kwargs(platform, kwargs)
    if legacy_chip:
        return f"{platform}:{legacy_chip}"

    # Truly bare provider — surface a helpful error pointing at known chips.
    suggestions: list[str] = []
    try:
        from uniqc.backend_adapter.backend_cache import get_cached_backends
        from uniqc.backend_adapter.backend_info import Platform

        cached = get_cached_backends(Platform(platform))
        suggestions = [f"{platform}:{entry.name}" for entry in cached][:6]
    except Exception:
        suggestions = []

    suggestion_msg = (
        f" Known chips in cache: {', '.join(suggestions)}."
        if suggestions
        else f" Run `uniqc backend list -p {platform}` to discover available chips."
    )
    raise BackendNotFoundError(
        f"Backend '{backend}' is missing a chip name. submit_task() requires "
        f"the canonical 'provider:chip-name' form, e.g. '{platform}:<CHIP>'."
        f"{suggestion_msg}"
    )


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
        backend: The backend identifier. Accepts the same forms as
            :func:`submit_task`, including ``'<platform>:<chip>'``
            (e.g. ``'originq:WK_C180'``, ``'dummy:originq:WK_C180'``).
        shots: Number of measurement shots for validation.
        **kwargs: Additional backend-specific parameters.
            - For IBM: chip_id (required for full validation)
            - For Quafu: chip_id (required for full validation)
            - For OriginQ: backend_name (e.g., 'WK_C180'). When ``backend``
              already contains the chip suffix (``'originq:WK_C180'``) the
              chip is extracted automatically and forwarded as
              ``backend_name``.

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
    # Strict pre-flight gate (same as submit_task / submit_batch).
    from uniqc.backend_adapter.preflight import (
        BackendPreflightError,
        ensure_backend_ready,
    )
    try:
        ensure_backend_ready(backend)
    except (BackendPreflightError, ValueError) as exc:
        return DryRunResult(
            success=False,
            details=f"Pre-flight check failed: {exc}",
            error=str(exc),
            error_kind="preflight",
            backend_name=backend,
        )

    from uniqc.backend_adapter.task.adapters.dummy_adapter import DummyAdapter

    # Dummy backends still need their special init path because they pull
    # chip_characterization / noise_model / available_qubits from kwargs.
    if backend.startswith("dummy:"):
        try:
            from uniqc.backend_adapter.dummy_backend import dummy_adapter_kwargs

            adapter: QuantumAdapter = DummyAdapter(
                **dummy_adapter_kwargs(
                    backend,
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
                error_kind="adapter_init",
                backend_name="dummy",
            )
        forwarded_kwargs = dict(kwargs)
    else:
        # Reuse the same adapter resolver as submit_task so that
        # 'originq:WK_C180' works in both APIs.
        platform = backend.split(":", 1)[0] if ":" in backend else backend
        chip = backend.split(":", 1)[1] if ":" in backend else None
        try:
            adapter = _get_adapter(backend)
        except BackendNotFoundError as e:
            return DryRunResult(
                success=False,
                details=str(e),
                error=str(e),
                error_kind="unknown_backend",
                warnings=("Known backends: originq, quafu, quark, ibm, dummy",),
            )
        except (ImportError, ModuleNotFoundError) as e:
            if str(platform) == "quafu":
                hint = (
                    "The Quafu adapter is deprecated; install pyquafu directly "
                    "if you still need it: `pip install pyquafu` (pulls numpy<2)."
                )
            elif str(platform) in ("qiskit", "ibm"):
                hint = (
                    "Qiskit is a core dependency of unified-quantum; the install "
                    "appears broken. Reinstall with `pip install --upgrade unified-quantum`."
                )
            else:
                hint = (
                    f"Install the matching extra (e.g. "
                    f"`pip install \"unified-quantum[{platform}]\"`)."
                )
            return DryRunResult(
                success=False,
                details=f"Adapter for '{backend}' is not installed. {hint}",
                error=str(e),
                error_kind="sdk_missing",
            )
        except Exception as e:  # noqa: BLE001
            return DryRunResult(
                success=False,
                details=f"Failed to initialize adapter for '{backend}': {e}",
                error=str(e),
                error_kind="adapter_init",
            )

        # If the user passed 'originq:WK_C180' we forward the chip via
        # backend_name kwarg so the adapter validates the right device.
        forwarded_kwargs = dict(kwargs)
        if chip is not None and "backend_name" not in forwarded_kwargs:
            forwarded_kwargs["backend_name"] = chip

    originir = circuit.originir
    try:
        return adapter.dry_run(originir, shots=shots, **forwarded_kwargs)
    except (ImportError, ModuleNotFoundError) as e:
        return DryRunResult(
            success=False,
            details=(
                f"dry_run() needs an SDK that is not installed: {e}. "
                f"Install the matching extra and retry."
            ),
            error=str(e),
            error_kind="sdk_missing",
            backend_name=getattr(adapter, "name", None),
        )
    except Exception as e:
        return DryRunResult(
            success=False,
            details=f"dry_run() raised an unhandled exception: {e}",
            error=str(e),
            error_kind="unknown",
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
    already resolved it. Chip-name lookup is case-insensitive so that
    ``originq:wk_c180`` and ``originq:WK_C180`` both resolve to the same
    cached entry.
    """
    explicit = kwargs.get("backend_info")
    if explicit is not None:
        return explicit
    if backend.startswith("dummy:"):
        return None
    try:
        from uniqc.backend_adapter.backend_cache import get_cached_backends, is_stale
        from uniqc.backend_adapter.backend_info import Platform, parse_backend_id

        try:
            platform, name = parse_backend_id(backend)
        except ValueError:
            # Bare 'platform' form — try to combine with a chip kwarg so we
            # can still resolve the BackendInfo for legacy callers.
            platform_key = backend.split(":", 1)[0]
            try:
                platform = Platform(platform_key)
            except ValueError:
                return None
            chip = _chip_from_kwargs(platform_key, kwargs)
            if not chip:
                return None
            name = chip
    except Exception:
        return None
    if platform == Platform.DUMMY:
        return None
    try:
        cached = get_cached_backends(platform)
    except Exception:
        return None
    fresh = not is_stale(platform.value)
    name_ci = name.casefold()
    for entry in cached:
        if entry.name == name or entry.name.casefold() == name_ci:
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
    local_compile: int = 1,
) -> tuple[Circuit, dict[str, Any]]:
    """Validate a circuit against ``backend`` and optionally compile it locally.

    Returns ``(circuit, metadata_extras)``. The returned circuit is either the
    original (when ``local_compile == 0`` or when it already satisfies the
    backend's gate set / topology) or a freshly-compiled circuit produced by
    :func:`uniqc.compile.compile_for_backend` at ``optimization_level=local_compile``.

    Raises :class:`uniqc.exceptions.UnsupportedGateError` only when the circuit
    is incompatible with the *target IR language* (e.g. ``RPhi`` → QASM2-only
    platforms — there is no representation for it). All other validation
    failures are surfaced as warnings; if ``local_compile > 0`` the circuit
    is rewritten through qiskit transpile to satisfy them, otherwise it is
    submitted as-is and the cloud platform is left to handle compilation.

    Parameters
    ----------
    local_compile : int
        ``0`` skips local compilation entirely (no qiskit transpile pass).
        ``1``-``3`` runs qiskit transpile at the corresponding optimization
        level when basis-gate or topology validation fails. Higher values
        cost more CPU time but generally yield shorter / higher-fidelity
        circuits.
    """
    if backend.startswith("dummy:"):
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
    extras["local_compile"] = local_compile

    if backend_info is not None and backend_info.extra.get("_uniqc_topology_stale"):
        extras["topology_stale"] = True
        extras["validation_warnings"].append(
            f"Backend topology cache for {backend} is stale (older than TTL); "
            "consider running `uniqc backend update`."
        )

    if report.compatible:
        return circuit, extras

    # Validation failed but local_compile=0 → submit as-is (cloud will compile).
    if local_compile <= 0:
        extras["validation_warnings"].append(
            f"Circuit not in basis gates / topology for '{backend}', but "
            f"local_compile=0; submitting untransformed and relying on cloud."
        )
        return circuit, extras

    if backend_info is None:
        from uniqc.exceptions import UnsupportedGateError

        msg = "; ".join(report.errors) or "validation failed"
        raise UnsupportedGateError(
            f"Circuit is not compatible with backend '{backend}': {msg}. "
            f"local_compile={local_compile} requested but no backend_info "
            f"available to compile against."
        )

    # Try compiling and re-validate.
    try:
        compiled = compile_for_backend(
            circuit, backend_info, level=local_compile
        )
    except Exception as exc:  # pragma: no cover - depends on optional qiskit
        from uniqc.exceptions import UnsupportedGateError

        raise UnsupportedGateError(
            f"Circuit failed validation for '{backend}' and "
            f"local_compile={local_compile} errored: {exc}"
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


def _active_qubits_from_originir(originir: str) -> set[int]:
    """Best-effort scan of an OriginIR string for qubits actually touched
    by gates (not counting unused logical slots from a generous QINIT)."""
    import re
    pattern = re.compile(r"q\[(\d+)\]")
    active: set[int] = set()
    for line in originir.splitlines():
        s = line.strip()
        if not s or s.startswith("QINIT") or s.startswith("CREG"):
            continue
        for m in pattern.finditer(s):
            active.add(int(m.group(1)))
    return active


def _compile_for_chip_backed_dummy(
    circuit: Circuit,
    spec: Any,
    metadata: dict | None,
    *,
    local_compile: int = 1,
    available_qubits: list[int] | tuple[int, ...] | None = None,
) -> tuple[str, dict]:
    """Compile source circuit when a dummy target mirrors a real chip.

    Honours the standard ``local_compile`` contract: ``local_compile=0``
    skips the qiskit transpile + relayout entirely so the user's
    physical-qubit choice is preserved verbatim. Any value ``> 0`` runs
    the full chip-aware compile at qiskit ``optimization_level=2``.

    When ``available_qubits`` is given (typically forwarded from the
    user's ``submit_task`` kwargs that already constrain the dummy
    simulator), the layout pass is restricted to that physical-qubit
    subset so the relayout cannot land on chip-but-disabled qubits. As
    an additional safety rule, if the source circuit's actually-touched
    qubits are all already inside ``available_qubits``, the IR is
    passed through verbatim regardless of ``local_compile`` — the user
    has hand-picked a valid layout and we MUST NOT silently relabel
    onto different physical qubits (the original bug that prompted
    NEW-U1 / NEW-U2: q[58] silently moved to q[13] on a chip whose
    q[13] had been excluded as bad).
    """
    enriched = dict(metadata or {})

    # Resolve the effective allow-list once: explicit kwarg > spec.
    effective_available = (
        available_qubits if available_qubits is not None else spec.available_qubits
    )

    source_originir = circuit.originir

    # Pass-through cases:
    if local_compile == 0:
        return source_originir, enriched
    if spec.source_platform is None or spec.chip_characterization is None:
        return source_originir, enriched
    if effective_available is not None:
        active = _active_qubits_from_originir(source_originir)
        allowed = {int(q) for q in effective_available}
        if active and active.issubset(allowed):
            # User picked the layout. Don't relabel.
            enriched.setdefault("compile_passthrough_reason",
                                "active qubits already inside available_qubits")
            return source_originir, enriched

    from uniqc.compile import compile as compile_circuit

    backend_info = _backend_info_from_chip(spec)
    compiled_originir = compile_circuit(
        circuit,
        backend_info=backend_info,
        chip_characterization=spec.chip_characterization,
        output_format="originir",
        available_qubits=effective_available,
    )
    enriched.setdefault("compiled_circuit_ir", compiled_originir)
    enriched.setdefault("compiled_circuit_language", "OriginIR")
    enriched.setdefault("executed_circuit_ir", compiled_originir)
    enriched.setdefault("executed_circuit_language", "OriginIR")
    enriched.setdefault("compile_target_backend", f"{spec.source_platform.value}:{spec.source_name}")
    return compiled_originir, enriched


def submit_task(
    circuit: Circuit | str,
    backend: str,
    shots: int = 1000,
    metadata: dict | None = None,
    options: BackendOptions | dict | None = None,
    *,
    local_compile: int = 1,
    cloud_compile: int = 1,
    backend_name: str | None = None,
    chip_id: str | None = None,
    **kwargs: Any,
) -> str:
    """Submit a single circuit to a quantum backend.

    This function performs IR-language validation, optionally rewrites the
    circuit through a local qiskit transpile pass, then ships the result to
    the backend's native API.

    Args:
        circuit: The UnifiedQuantum Circuit to submit.
        backend: Backend identifier in the canonical ``'provider:chip-name'``
            format (e.g. ``'originq:WK_C180'``, ``'quafu:ScQ-P10'``,
            ``'ibm:ibm_brisbane'``). Cloud submissions reject the bare
            ``'provider'`` form (e.g. ``'originq'``) and surface the list
            of cached chips for that provider — call
            ``uniqc.list_backends()`` or run ``uniqc backend list -p
            originq`` to discover available chips. Dummy backends use
            ``'dummy'`` or ``'dummy:<provider>:<chip>'`` and are exempt
            from the strict format check.
        shots: Number of measurement shots.
        metadata: Optional metadata to store with the task.
        options: Optional typed backend options. Accepts a
            :class:`BackendOptions` instance, a plain dict (treated as
            ``**kwargs``), or ``None`` for platform defaults.
        local_compile: Local qiskit transpile pass strength.

            - ``0`` — no local transpile. The circuit is shipped as-authored
              (after IR-language validation). Use this when you have
              hand-tuned the circuit or want to delegate everything to the
              cloud transpiler.
            - ``1`` (default) — light qiskit transpile to the chip's basis
              gates and topology when validation fails.
            - ``2`` / ``3`` — heavier qiskit optimization. Slower but yields
              shorter / higher-fidelity circuits.

            See ``docs/source/compile/compile_levels.md`` for details on what
            each level does.
        cloud_compile: Cloud-side compile request strength forwarded to the
            adapter. ``0`` disables cloud compile (e.g.
            ``OriginQAdapter`` receives ``circuit_optimize=False``); any
            value ``> 0`` enables it (boolean cloud APIs see ``True``).
            Adapters with finer control may interpret ``1``/``2``/``3``
            directly.
        backend_name: OriginQ chip name (e.g. ``'WK_C180'``). Optional when
            ``backend`` already encodes the chip as ``'originq:<chip>'``.
        chip_id: Quafu / IBM chip ID. Required for full validation on those
            platforms.
        **kwargs: Additional backend-specific parameters passed through to
            the underlying adapter. Common implicit / hidden defaults:

            - ``skip_validation`` (default ``False``): bypass the offline
              IR-language compatibility check. Use sparingly — most
              validation failures are real bugs.
            - For Quafu: ``chip_id``, ``auto_mapping``
            - For OriginQ: ``backend_name`` (e.g. ``'WK_C180'``),
              ``measurement_amend``
            - For dummy: ``chip_characterization``, ``noise_model``,
              ``available_qubits``, ``available_topology``

    Returns:
        The task ID assigned by the backend.

    Raises:
        BackendNotFoundError: If the backend identifier is missing a chip
            name (bare ``'provider'``) or is otherwise unrecognised.
        BackendNotAvailableError: If the backend is not available.
        UnsupportedGateError: If the circuit uses gates that cannot be
            expressed in the backend's IR language (hard block — never
            skippable, no amount of local/cloud compile can help).
        AuthenticationError: If authentication fails.
        InsufficientCreditsError: If account has insufficient credits.
        QuotaExceededError: If usage quota is exceeded.
        NetworkError: If a network error occurs.

    Example:
        >>> circuit = Circuit()
        >>> circuit.h(0)
        >>> circuit.cnot(0, 1)
        >>> circuit.measure(0, 1)
        >>> # Canonical form (preferred):
        >>> task_id = submit_task(circuit, backend='originq:WK_C180', shots=1000)
        >>> # Legacy form (still accepted, normalised internally):
        >>> task_id = submit_task(circuit, backend='originq', backend_name='WK_C180', shots=1000)
        >>> # Heavier local compile, no cloud-side recompile:
        >>> task_id = submit_task(
        ...     circuit, backend='originq:WK_C180', shots=1000,
        ...     local_compile=3, cloud_compile=0,
        ... )
        >>> # Local noisy simulation using chip characterization:
        >>> from uniqc.backend_adapter.task.adapters.originq_adapter import OriginQAdapter
        >>> chip = OriginQAdapter().get_chip_characterization("WK_C180")
        >>> task_id = submit_task(circuit, backend='dummy:local:simulator', chip_characterization=chip)
    """
    import warnings

    # Normalize input: accept Circuit, OriginIR str, QASM str, qiskit.QuantumCircuit.
    circuit = _normalize_circuit_input(circuit)

    # Strict pre-flight gate: missing SDK / chip cache → loud error.
    # Tests / scripts that pass "dummy:<provider>:<chip>" without the
    # provider SDK installed will fail here instead of silently working.
    from uniqc.backend_adapter.preflight import (
        BackendPreflightError,
        ensure_backend_ready,
    )
    try:
        ensure_backend_ready(backend)
    except (BackendPreflightError, ValueError):
        # Re-raise with the same type so callers can distinguish.
        raise

    # Re-pack the explicit kwargs into the kwargs dict so the existing
    # adapter wiring keeps working unchanged.
    if backend_name is not None:
        kwargs.setdefault("backend_name", backend_name)
    if chip_id is not None:
        kwargs.setdefault("chip_id", chip_id)

    # Cloud-side compile flag → adapter kwarg. Boolean cloud APIs see
    # bool(cloud_compile > 0); richer adapters can read the int directly.
    kwargs.setdefault("circuit_optimize", cloud_compile > 0)
    kwargs["cloud_compile"] = cloud_compile

    # Normalise options
    if options is not None:
        opts = BackendOptionsFactory.normalize_options(options, _backend_platform_key(backend))
        merged_kwargs = opts.to_kwargs()
        merged_kwargs.update(kwargs)
        kwargs = merged_kwargs
        shots = opts.shots

    metadata = _metadata_with_circuit(circuit, metadata)

    # Generate the uniqc-managed task id up front. This is the ID we
    # return to the caller; it maps internally to one or more
    # platform-issued task ids via the ``task_shards`` table.
    uniqc_task_id = generate_uniqc_task_id()

    # Route dummy backend through _submit_dummy which pre-populates the result.
    # This ensures 'uniqc result <task_id>' returns data immediately without
    # needing a subsequent query against a cloud backend.
    if backend.startswith("dummy:"):
        kwargs.pop("cloud_compile", None)
        return _submit_dummy(circuit, backend, shots=shots, metadata=metadata,
                             local_compile=local_compile,
                             uniqc_task_id=uniqc_task_id, **kwargs)

    # Enforce 'provider:chip' canonical form for cloud submissions and inject
    # the chip into adapter kwargs so downstream calls don't fall back to a
    # default chip silently.
    backend = _require_qualified_backend(backend, kwargs)

    # Pre-submission validation + optional local compile.
    circuit, prep_extras = _prepare_circuit_for_submission(
        circuit, backend, kwargs, local_compile=local_compile
    )
    metadata = {**metadata, **prep_extras}

    # Persist a parent task row BEFORE remote submission so that any
    # mid-submit failure leaves a discoverable parent the caller can
    # still query / inspect.
    task_info = TaskInfo(
        task_id=uniqc_task_id,
        backend=backend,
        status=TaskStatus.PENDING,
        shots=shots,
        metadata=metadata or {},
    )
    save_task(task_info)

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

    # Strip uniqc-internal kwargs that adapters don't accept.
    kwargs.pop("cloud_compile", None)

    # Submit to backend
    try:
        platform_task_id = backend_instance.submit(native_circuit, shots=shots, **kwargs)
    except Exception as e:
        # Mark the parent FAILED with submission_error metadata so the
        # uniqc id is still discoverable — important for debugging
        # transient cloud errors.
        task_info.status = TaskStatus.FAILED
        task_info.error_message = f"submit failed: {e!r}"
        task_info.metadata = {**(task_info.metadata or {}),
                              "submission_error": str(e)}
        save_task(task_info)
        mapped_error = _map_adapter_error(e, backend)
        raise mapped_error from e

    # Persist a single shard row mapping the uniqc id to the platform id.
    shard = TaskShard(
        uniqc_task_id=uniqc_task_id,
        shard_index=0,
        platform_task_id=platform_task_id,
        backend=backend,
        circuit_count=1,
        sub_index_offset=0,
        status=TaskStatus.RUNNING,
    )
    _store().save_shard(shard)

    # Promote parent to RUNNING now that we have at least one shard.
    task_info.status = TaskStatus.RUNNING
    save_task(task_info)

    return uniqc_task_id


def _submit_dummy(
    circuit: Circuit,
    backend: str,
    shots: int = 1000,
    metadata: dict | None = None,
    *,
    local_compile: int = 1,
    uniqc_task_id: str | None = None,
    **kwargs: Any,
) -> str:
    """Submit a circuit using the dummy adapter for local simulation.

    Args:
        circuit: The UnifiedQuantum Circuit to simulate.
        backend: The backend name (used for logging/metadata only).
        shots: Number of measurement shots.
        metadata: Optional metadata.
        uniqc_task_id: Pre-generated uniqc task id to associate this
            shard with. When ``None`` a fresh id is allocated.
        **kwargs: Additional parameters (passed to dummy adapter).

    Returns:
        The uniqc task id ``uqt_*`` mapped to the dummy platform id.
    """
    from uniqc.backend_adapter.dummy_backend import dummy_adapter_kwargs, resolve_dummy_backend
    from uniqc.backend_adapter.task.adapters.dummy_adapter import DummyAdapter

    if uniqc_task_id is None:
        uniqc_task_id = generate_uniqc_task_id()

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

    originir, metadata = _compile_for_chip_backed_dummy(
        circuit, spec, metadata,
        local_compile=local_compile,
        available_qubits=kwargs.get("available_qubits"),
    )
    platform_task_id = dummy_adapter.submit(originir, shots=shots)

    # Get result from dummy adapter
    result = dummy_adapter.query(platform_task_id)
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

    # Create and save task info under the uniqc id.
    task_info = TaskInfo(
        task_id=uniqc_task_id,
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
    elif adapter_status == TASK_STATUS_FAILED:
        task_info.error_message = result.get("error_message") or result.get("error")

    save_task(task_info)

    # Persist a single shard row pointing at the dummy platform id.
    shard = TaskShard(
        uniqc_task_id=uniqc_task_id,
        shard_index=0,
        platform_task_id=platform_task_id,
        backend=spec.identifier,
        circuit_count=1,
        sub_index_offset=0,
        status=task_status,
        result=result.get("result"),
        error_message=task_info.error_message,
    )
    _store().save_shard(shard)

    return uniqc_task_id


def submit_batch(
    circuits: list[Circuit | str],
    backend: str,
    shots: int = 1000,
    options: BackendOptions | dict | None = None,
    *,
    local_compile: int = 1,
    cloud_compile: int = 1,
    backend_name: str | None = None,
    chip_id: str | None = None,
    native_batch: bool = True,
    return_platform_ids: bool = False,
    **kwargs: Any,
) -> str | list[str]:
    """Submit multiple circuits as a batch and return a single uniqc task id.

    uniqc maintains an internal mapping from one ``uqt_*`` task id to one
    or more platform-issued task ids. The user manages exactly **one**
    handle, regardless of the underlying platform's batch capabilities:

    * For platforms with native batch (OriginQ, IBM) — circuits are packed
      into one platform job per shard. uniqc auto-shards if the batch
      exceeds the adapter's :attr:`max_native_batch_size` (e.g. OriginQ
      ``task_group_size`` 200, IBM 100).
    * For platforms without native batch (Quafu, Quark, Dummy) —
      ``max_native_batch_size = 1``: uniqc loops one platform job per
      circuit, but the user still receives a single ``uqt_*`` id and
      :func:`wait_for_result` returns the per-circuit results in
      submission order.

    Args:
        circuits: List of UnifiedQuantum Circuits to submit.
        backend: The backend name.
        shots: Number of measurement shots per circuit.
        options: Optional typed backend options. Same as in :func:`submit_task`.
        local_compile: Local qiskit transpile pass strength. See
            :func:`submit_task` for the full semantics. Default ``1``.
        cloud_compile: Cloud-side compile request strength. See
            :func:`submit_task`. Default ``1``.
        backend_name: OriginQ chip name (optional when ``backend`` already
            encodes the chip).
        chip_id: Quafu / IBM chip ID.
        native_batch: When ``True`` (default), shards use the platform's
            native grouped-submission API (one platform job per shard).
            When ``False``, every circuit is submitted as a separate
            platform job (one shard per circuit). Useful when you need
            to retry/cancel individual circuits but do not need
            per-circuit task ids returned.
        return_platform_ids: When ``True``, returns the list of
            platform-issued task ids (one per shard, NOT one per
            circuit). Provided only for legacy code paths and debugging;
            new code should always use the single returned ``uqt_*`` id
            and call :func:`get_platform_task_ids` if it needs the
            mapping.
        **kwargs: Additional backend-specific parameters.

    Returns:
        The uniqc task id ``uqt_*`` for this batch, or a list of platform
        task ids when ``return_platform_ids=True``.

    Example:
        >>> circuits = [build(i) for i in range(400)]
        >>> uid = submit_batch(circuits, 'originq', shots=1000,
        ...                    backend_name='WK_C180')
        >>> # `uid` is one ``uqt_*`` covering up to ``ceil(400/200) = 2`` shards
        >>> results = wait_for_result(uid)         # list[UnifiedResult] len=400
        >>> shards  = get_platform_task_ids(uid)   # 2 shard rows
    """
    # Normalize inputs: accept Circuit, OriginIR str, QASM str, qiskit.QuantumCircuit.
    circuits = [_normalize_circuit_input(c) for c in circuits]

    # Strict pre-flight gate (same as submit_task).
    from uniqc.backend_adapter.preflight import (
        BackendPreflightError,
        ensure_backend_ready,
    )
    try:
        ensure_backend_ready(backend)
    except (BackendPreflightError, ValueError):
        raise

    # Re-pack explicit kwargs.
    if backend_name is not None:
        kwargs.setdefault("backend_name", backend_name)
    if chip_id is not None:
        kwargs.setdefault("chip_id", chip_id)
    kwargs.setdefault("circuit_optimize", cloud_compile > 0)
    kwargs["cloud_compile"] = cloud_compile
    kwargs["native_batch"] = native_batch

    # Normalise options
    if options is not None:
        opts = BackendOptionsFactory.normalize_options(options, _backend_platform_key(backend))
        merged_kwargs = opts.to_kwargs()
        merged_kwargs.update(kwargs)
        kwargs = merged_kwargs
        shots = opts.shots

    # Pre-allocate the uniqc id; it is the single handle returned to the user.
    uniqc_task_id = generate_uniqc_task_id()

    # Route dummy backend to _submit_batch_dummy which pre-populates results.
    if backend.startswith("dummy:"):
        kwargs.pop("cloud_compile", None)
        kwargs.pop("native_batch", None)
        result_id = _submit_batch_dummy(
            circuits, backend, shots=shots, local_compile=local_compile,
            uniqc_task_id=uniqc_task_id, **kwargs,
        )
        if return_platform_ids:
            return [s.platform_task_id for s in _store().get_shards(result_id)]
        return result_id

    # Enforce 'provider:chip' canonical form for cloud submissions and inject
    # the chip into adapter kwargs.
    backend = _require_qualified_backend(backend, kwargs)

    # Pre-submission validation for each circuit; local-compile any that fail.
    prepared: list[Circuit] = []
    prep_extras_list: list[dict[str, Any]] = []
    for c in circuits:
        c2, extras = _prepare_circuit_for_submission(
            c, backend, kwargs, local_compile=local_compile
        )
        prepared.append(c2)
        prep_extras_list.append(extras)
    circuits = prepared

    # Persist the parent task row immediately so that any mid-submit
    # failure leaves the uniqc id queryable.
    parent_metadata: dict[str, Any] = {
        "batch": True,
        "batch_size": len(circuits),
        "circuits": [
            _metadata_with_circuit(c, {})["circuit_ir"] for c in circuits
        ],
        "circuit_language": "OriginIR",
    }
    parent_info = TaskInfo(
        task_id=uniqc_task_id,
        backend=backend,
        status=TaskStatus.PENDING,
        shots=shots,
        metadata=parent_metadata,
    )
    save_task(parent_info)

    # Resolve backend instance
    try:
        backend_instance = backend_module.get_backend(backend)
    except ValueError as e:
        raise BackendNotFoundError(str(e)) from e

    if not backend_instance.is_available():
        raise BackendNotAvailableError(
            f"Backend '{backend}' is not available. Please check your configuration and credentials."
        )

    try:
        adapter = _get_adapter(backend)
        native_circuits = adapter.adapt_batch(circuits)
    except Exception as e:
        raise _map_adapter_error(e, backend) from e

    # Decide shard size. ``native_batch=False`` forces one circuit per
    # platform job (i.e. shard size 1). Otherwise honour the adapter's
    # ``max_native_batch_size`` (an instance attribute or class attr).
    task_adapter = backend_instance.adapter  # the QuantumAdapter instance
    max_size = max(1, int(getattr(task_adapter, "max_native_batch_size", 1)))
    shard_size = 1 if not native_batch else max_size

    kwargs.pop("cloud_compile", None)

    shards_submitted: list[TaskShard] = []
    try:
        for shard_index, start in enumerate(range(0, len(native_circuits), shard_size)):
            chunk = native_circuits[start:start + shard_size]
            chunk_shots = shots
            try:
                result = backend_instance.submit_batch(
                    chunk, shots=chunk_shots, **kwargs,
                )
            except Exception as exc:
                # Mark parent FAILED with submission_error and the list
                # of already-submitted shards so the user can still
                # query/cancel them.
                parent_info.status = TaskStatus.FAILED
                parent_info.error_message = (
                    f"Shard {shard_index}/{ -(-len(native_circuits) // shard_size) } "
                    f"submit failed: {exc!r}"
                )
                parent_info.metadata = {
                    **(parent_info.metadata or {}),
                    "submission_error": str(exc),
                    "partial_submitted_shards": [
                        s.platform_task_id for s in shards_submitted
                    ],
                }
                save_task(parent_info)
                mapped_error = _map_adapter_error(exc, backend)
                raise mapped_error from exc

            # Adapters may return ``str`` (one platform job) or a list of
            # ``str`` for non-native-batch shards (one platform job per
            # circuit). Normalise to list, then pack into shard rows.
            ids = result if isinstance(result, list) else [result]
            if len(ids) == 1:
                # Single platform job covers the whole shard chunk.
                shard = TaskShard(
                    uniqc_task_id=uniqc_task_id,
                    shard_index=shard_index,
                    platform_task_id=ids[0],
                    backend=backend,
                    circuit_count=len(chunk),
                    sub_index_offset=start,
                    status=TaskStatus.RUNNING,
                )
                _store().save_shard(shard)
                shards_submitted.append(shard)
            else:
                # Adapter expanded to one job per circuit even though we
                # asked for native batch (e.g. native_batch=False or
                # adapter has max_native_batch_size=1). Each platform id
                # becomes its own shard with circuit_count=1.
                for offset, pid in enumerate(ids):
                    shard = TaskShard(
                        uniqc_task_id=uniqc_task_id,
                        shard_index=len(shards_submitted),
                        platform_task_id=pid,
                        backend=backend,
                        circuit_count=1,
                        sub_index_offset=start + offset,
                        status=TaskStatus.RUNNING,
                    )
                    _store().save_shard(shard)
                    shards_submitted.append(shard)

        # All shards submitted successfully → parent is RUNNING.
        parent_info.status = TaskStatus.RUNNING
        save_task(parent_info)
    except Exception:
        raise

    if return_platform_ids:
        return [s.platform_task_id for s in shards_submitted]
    return uniqc_task_id


def _submit_batch_dummy(
    circuits: list[Circuit],
    backend: str,
    shots: int = 1000,
    *,
    local_compile: int = 1,
    uniqc_task_id: str | None = None,
    **kwargs: Any,
) -> str:
    """Submit multiple circuits using the dummy adapter.

    Returns the parent ``uqt_*`` id; per-circuit dummy platform ids are
    persisted as one shard each so :func:`wait_for_result` can return a
    ``list[UnifiedResult]`` in submission order.
    """
    from uniqc.backend_adapter.dummy_backend import dummy_adapter_kwargs, resolve_dummy_backend
    from uniqc.backend_adapter.task.adapters.dummy_adapter import DummyAdapter

    if uniqc_task_id is None:
        uniqc_task_id = generate_uniqc_task_id()

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
        originir, item_metadata = _compile_for_chip_backed_dummy(
            circuit, spec, {},
            local_compile=local_compile,
            available_qubits=kwargs.get("available_qubits"),
        )
        originir_circuits.append(originir)
        compiled_metadata.append(item_metadata)
    platform_ids = dummy_adapter.submit_batch(originir_circuits, shots=shots)

    # Aggregate parent metadata.
    parent_metadata: dict[str, Any] = {
        "batch": True,
        "batch_size": len(circuits),
        "circuits": [
            _metadata_with_circuit(c, {})["circuit_ir"] for c in circuits
        ],
        "circuit_language": "OriginIR",
        "dummy_backend_id": spec.identifier,
        "dummy_noise_source": spec.noise_source,
        "dummy_source_backend": (
            f"{spec.source_platform.value}:{spec.source_name}"
            if spec.source_platform is not None and spec.source_name
            else None
        ),
    }

    # Persist parent FIRST so the FK from task_shards.uniqc_task_id is
    # satisfied. Initial status PENDING will be replaced with the
    # aggregated value once shards are written.
    parent_info = TaskInfo(
        task_id=uniqc_task_id,
        backend=spec.identifier,
        status=TaskStatus.PENDING,
        shots=shots,
        metadata=parent_metadata,
    )
    save_task(parent_info)

    status_map = {
        TASK_STATUS_SUCCESS: TaskStatus.SUCCESS,
        TASK_STATUS_FAILED: TaskStatus.FAILED,
        TASK_STATUS_RUNNING: TaskStatus.RUNNING,
    }

    # Persist one shard per circuit.
    for index, platform_id in enumerate(platform_ids):
        result = dummy_adapter.query(platform_id)
        adapter_status = result.get("status", TASK_STATUS_RUNNING)
        shard_status = status_map.get(adapter_status, TaskStatus.FAILED)
        shard = TaskShard(
            uniqc_task_id=uniqc_task_id,
            shard_index=index,
            platform_task_id=platform_id,
            backend=spec.identifier,
            circuit_count=1,
            sub_index_offset=index,
            status=shard_status,
            result=result.get("result") if adapter_status == TASK_STATUS_SUCCESS else None,
            error_message=(
                _extract_error_message(result)
                if adapter_status == TASK_STATUS_FAILED else None
            ),
        )
        _store().save_shard(shard)

    # Aggregate parent status from saved shards and persist.
    shards = _store().get_shards(uniqc_task_id)
    parent_info.status = TaskStore.aggregate_status(shards)
    if parent_info.status == TaskStatus.SUCCESS.value:
        parent_info.result = [s.result for s in shards]
    save_task(parent_info)

    return uniqc_task_id


# -----------------------------------------------------------------------------
# Task Query
# -----------------------------------------------------------------------------


def _resolve_to_uniqc_id(task_id: str) -> tuple[str, bool]:
    """Resolve ``task_id`` to a uniqc parent id.

    Returns ``(uniqc_id, is_legacy_alias)``. When the input was a
    platform task id discovered via the shard index, ``is_legacy_alias``
    is ``True`` and a one-shot ``DeprecationWarning`` is emitted.

    Raises ``TaskNotFoundError`` if neither path resolves.
    """
    if is_uniqc_task_id(task_id):
        return task_id, False
    # Try platform-id lookup via the shard index.
    found = _store().find_uniqc_id_by_platform_id(task_id)
    if found is not None:
        import warnings
        warnings.warn(
            f"Task lookup via platform id {task_id!r} is deprecated; "
            f"use the uniqc id {found!r} instead. The platform id will "
            "still resolve via the shard index but this fallback may "
            "be removed in a future release.",
            DeprecationWarning,
            stacklevel=3,
        )
        return found, True
    # Fall through to legacy direct path — caller's job to handle missing.
    return task_id, False


def get_platform_task_ids(task_id: str) -> list[TaskShard]:
    """Return the shard mapping for a uniqc task id.

    Each :class:`TaskShard` records:

    * ``platform_task_id`` — the id assigned by the cloud platform
    * ``shard_index`` — 0-based ordering within the parent
    * ``circuit_count`` — number of circuits packed into this shard
    * ``sub_index_offset`` — index of this shard's first circuit in the
      original :func:`submit_batch` list
    * ``status`` / ``error_message`` — per-shard liveness

    Args:
        task_id: A uniqc task id (``uqt_*``). For backwards compatibility
            this will also accept a platform task id and emit a
            :class:`DeprecationWarning` while resolving the parent.

    Returns:
        Shards in submission order. Empty list when the task has no
        shards yet (e.g. submission failed before any shard was
        persisted) or when ``task_id`` is unknown.
    """
    uniqc_id, _ = _resolve_to_uniqc_id(task_id)
    return _store().get_shards(uniqc_id)


def _extract_error_message(query_result: dict) -> str | None:
    """Extract a human-readable error message from an adapter query result.

    Adapters use slightly different layouts when a task fails:

    * OriginQ batch:    ``{"status": "failed", "result": {"error": "..."}}``
    * OriginQ single:   ``{"status": "failed", "result": {"error": "..."}}``
    * Generic fallback: ``{"status": "failed", "error": "..."}`` or
                        ``{"status": "failed", "message": "..."}``
    """
    inner = query_result.get("result")
    if isinstance(inner, dict):
        for key in ("error", "error_message", "message"):
            val = inner.get(key)
            if val:
                return str(val)
    for key in ("error_message", "error", "message"):
        val = query_result.get(key)
        if val:
            return str(val)
    return None


def _refresh_shard_from_backend(shard: TaskShard) -> TaskShard:
    """Best-effort refresh of a single shard's status from its backend.

    Updates ``shard`` in place and persists it. Network/auth errors are
    swallowed and the previous status is preserved — callers see the
    stale value rather than a hard failure.
    """
    if shard.status in TERMINAL_STATUSES:
        return shard
    try:
        backend_instance = backend_module.get_backend(shard.backend)
    except Exception:
        return shard
    try:
        result = backend_instance.query(shard.platform_task_id)
    except Exception:
        return shard
    adapter_status = result.get("status", TASK_STATUS_RUNNING)
    status_map = {
        TASK_STATUS_SUCCESS: TaskStatus.SUCCESS,
        TASK_STATUS_FAILED: TaskStatus.FAILED,
        TASK_STATUS_RUNNING: TaskStatus.RUNNING,
        "pending": TaskStatus.PENDING,
        "cancelled": TaskStatus.CANCELLED,
    }
    new_status = status_map.get(adapter_status, TaskStatus.RUNNING)
    shard.status = (
        new_status.value if isinstance(new_status, TaskStatus) else str(new_status)
    )
    if shard.status == TaskStatus.SUCCESS.value:
        shard.result = result.get("result")
        shard.error_message = None
    elif shard.status == TaskStatus.FAILED.value:
        shard.error_message = _extract_error_message(result)
        # Preserve the raw failure payload so debug output isn't lost.
        shard.result = result.get("result") if isinstance(result.get("result"), dict) else None
    _store().save_shard(shard)
    return shard


# Constant exported for external use (TERMINAL_STATUSES re-export from store).


def query_task(task_id: str, backend: str | None = None) -> TaskInfo:
    """Query the status of a task.

    For uniqc-managed task ids, refreshes each shard's status from its
    backend (best-effort), then denormalises the aggregate status onto
    the parent ``tasks`` row. The returned :class:`TaskInfo` therefore
    reflects the freshest known state.

    For legacy platform task ids (pre-v4 cache rows or rows without
    shards), falls back to the historical direct-query path.

    Args:
        task_id: The task identifier. Accepts a uniqc id (``uqt_*``)
            or, with a deprecation warning, a raw platform id.
        backend: Ignored when the task is found in cache (the backend
            is resolved from the stored shards). Only used for legacy
            direct-query fallback.

    Returns:
        :class:`TaskInfo` with current aggregated status.
    """
    cached_task = get_task(task_id)

    # Path A: uniqc id with one or more shards → aggregate from shards.
    if cached_task is not None and is_uniqc_task_id(task_id):
        shards = _store().get_shards(task_id)
        if shards:
            # Dummy tasks pre-store results at submit time; their shards
            # are already terminal so the refresh loop is a no-op.
            for shard in shards:
                _refresh_shard_from_backend(shard)
            shards = _store().get_shards(task_id)
            agg_status = TaskStore.aggregate_status(shards)
            cached_task.status = agg_status
            if agg_status == TaskStatus.SUCCESS.value:
                # Aggregate per-shard results into a flat list ordered by
                # ``sub_index_offset`` so wait_for_result can produce
                # the per-circuit UnifiedResult list directly.
                cached_task.result = _aggregate_shard_results(shards)
                cached_task.error_message = None
            elif agg_status == TaskStatus.FAILED.value:
                failed = [s for s in shards if s.status == TaskStatus.FAILED.value]
                msgs = [
                    f"shard {s.shard_index}: {s.error_message or 'failed'}"
                    for s in failed
                ]
                cached_task.error_message = "; ".join(msgs) or "shard(s) failed"
            save_task(cached_task)
            return cached_task

    # Path B: legacy / dummy direct path (no shards or non-uniqc id).
    if cached_task is not None:
        backend = cached_task.backend
        if backend.startswith("dummy:"):
            return cached_task

    # Path C: not in cache. Try resolving via platform-id alias first
    # (legacy support — emits DeprecationWarning).
    if cached_task is None and not is_uniqc_task_id(task_id):
        uniqc_id, was_alias = _resolve_to_uniqc_id(task_id)
        if was_alias:
            return query_task(uniqc_id, backend=backend)

    if backend is None:
        raise TaskNotFoundError(f"Task '{task_id}' not found in local cache. Please provide the backend parameter.")

    # Get backend instance (strip 'dummy:' prefix if present)
    actual_backend = backend
    try:
        backend_instance = backend_module.get_backend(actual_backend)
    except ValueError as e:
        raise BackendNotFoundError(str(e)) from e

    # Query backend (legacy direct path)
    try:
        result = backend_instance.query(task_id)
    except Exception as e:
        mapped_error = _map_adapter_error(e, backend)
        if isinstance(mapped_error, NetworkError):
            raise mapped_error from e
        cached_task = get_task(task_id)
        if cached_task is not None:
            return cached_task
        raise TaskNotFoundError(
            f"Task '{task_id}' not found: {e}",
            task_id=task_id,
        ) from e

    adapter_status = result.get("status", TASK_STATUS_RUNNING)
    status_map = {
        TASK_STATUS_SUCCESS: TaskStatus.SUCCESS,
        TASK_STATUS_FAILED: TaskStatus.FAILED,
        TASK_STATUS_RUNNING: TaskStatus.RUNNING,
        "pending": TaskStatus.PENDING,
        "cancelled": TaskStatus.CANCELLED,
    }
    task_status = status_map.get(adapter_status, TaskStatus.PENDING)

    task_info = TaskInfo(
        task_id=task_id,
        backend=backend,
        status=task_status,
        result=result.get("result") if task_status == TaskStatus.SUCCESS else None,
        error_message=(
            _extract_error_message(result)
        ) if task_status == TaskStatus.FAILED else None,
    )
    cached_task = get_task(task_id)
    if cached_task is not None:
        task_info.submit_time = cached_task.submit_time
        task_info.shots = cached_task.shots
        task_info.metadata = cached_task.metadata

    save_task(task_info)
    return task_info


def _aggregate_shard_results(shards: list[TaskShard]) -> Any:
    """Flatten shard results into a single per-circuit list.

    For shards with ``circuit_count == 1`` the shard's ``result`` is one
    dict (or a 1-element list — accept both). For native-batch shards
    with ``circuit_count > 1`` the shard's ``result`` is a list of
    counts dicts. We concatenate in ``sub_index_offset`` order. The
    returned list length equals the user's original batch size when all
    shards report the expected cardinality.

    If the parent represents a single-circuit submission (one shard,
    ``circuit_count == 1``) we return the single counts dict directly so
    that ``wait_for_result`` keeps returning a scalar
    :class:`UnifiedResult`.
    """
    ordered = sorted(shards, key=lambda s: s.sub_index_offset)
    if len(ordered) == 1 and ordered[0].circuit_count == 1:
        return ordered[0].result
    flat: list[Any] = []
    for s in ordered:
        if s.circuit_count == 1:
            flat.append(s.result)
        elif isinstance(s.result, list):
            if len(s.result) != s.circuit_count:
                # Surface the mismatch by padding/truncating to expected
                # length; downstream wrap will produce that many UR objects.
                items = list(s.result)
                while len(items) < s.circuit_count:
                    items.append(None)
                flat.extend(items[: s.circuit_count])
            else:
                flat.extend(s.result)
        else:
            # Unexpected shape — wrap as a single entry per circuit.
            for _ in range(s.circuit_count):
                flat.append(s.result)
    return flat


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

    For native batch jobs (one cloud task ID covering many circuits) the
    adapter returns ``result`` as a ``list[dict]`` — one counts dict per
    circuit. In that case use :func:`_wrap_as_unified_result_list`.
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


def _wrap_as_unified_result_list(
    raw: Any,
    task_id: str,
    backend: str | None,
    shots: int | None = None,
) -> list[UnifiedResult]:
    """Wrap a batch adapter result into a list of :class:`UnifiedResult`.

    Accepts:
      * ``list[dict[str, int]]`` — one counts dict per circuit
      * ``dict`` with ``"result": list[dict]`` wrapper
    """
    if isinstance(raw, dict) and isinstance(raw.get("result"), list):
        per_circuit = raw["result"]
    elif isinstance(raw, list):
        per_circuit = raw
    else:
        # Fall back to single-result wrapping in a list of length one.
        return [_wrap_as_unified_result(raw, task_id, backend, shots)]

    out: list[UnifiedResult] = []
    for idx, counts in enumerate(per_circuit):
        sub_id = f"{task_id}#{idx}"
        out.append(_wrap_as_unified_result(counts, sub_id, backend, shots))
    return out


def wait_for_result(
    task_id: str,
    timeout: float = 300.0,
    poll_interval: float = 5.0,
    raise_on_failure: bool = True,
) -> UnifiedResult | list[UnifiedResult] | None:
    """Wait for a task to complete and return its result.

    This function polls the task status until it completes, fails, or
    the timeout is reached. The backend is auto-resolved from the cached
    :class:`TaskInfo` — task IDs are unique, so explicit ``backend=`` is
    no longer needed.

    Args:
        task_id: The task identifier.
        timeout: Maximum time to wait in seconds.
        poll_interval: Time between status checks in seconds.
        raise_on_failure: If True, raises TaskFailedError on task failure.

    Returns:
        Single-circuit submissions return a :class:`UnifiedResult`.

        Native batch submissions (one cloud task ID covering many circuits,
        as produced by :func:`submit_batch` with ``native_batch=True``)
        return a ``list[UnifiedResult]`` — one entry per circuit, in the
        order they were submitted.

        Returns ``None`` if the task failed and ``raise_on_failure=False``.

        The :class:`UnifiedResult` object is dict-like (``result["00"]``,
        ``len(result)``, iteration, equality with a plain counts dict all
        work). Use :meth:`UnifiedResult.raw` to access the original
        platform-specific payload.

    Raises:
        TaskTimeoutError: If the timeout is reached before completion.
        TaskFailedError: If the task fails and raise_on_failure is True.
        TaskNotFoundError: If the task is not found.
        NetworkError: If a network error occurs.

    Example:
        >>> result = wait_for_result('task-123', timeout=300)
        >>> print(result.counts)        # unified accessor
        {'00': 512, '11': 488}
        >>> result['00']                # dict-like access still works
        512
        >>> result.raw()                # original adapter payload
        {'result': {'00': 512, '11': 488}, ...}

        Native batch result:

        >>> task_ids = submit_batch([c1, c2, c3], backend='originq:WK_C180')
        >>> results = wait_for_result(task_ids[0])
        >>> for r in results:
        ...     print(r.counts)
    """
    start_time = time.time()

    def _wrap(raw: Any, backend: str | None, shots: int | None,
              metadata: dict[str, Any] | None) -> UnifiedResult | list[UnifiedResult]:
        is_batch = bool(metadata and metadata.get("batch"))
        if is_batch and isinstance(raw, list):
            return _wrap_as_unified_result_list(
                raw, task_id=task_id, backend=backend, shots=shots,
            )
        return _wrap_as_unified_result(
            raw, task_id=task_id, backend=backend, shots=shots,
        )

    while True:
        # Query current status (backend auto-resolved from cache by task_id)
        task_info = query_task(task_id)
        backend = task_info.backend

        # Check if completed
        if task_info.status == TaskStatus.SUCCESS:
            return _wrap(task_info.result, task_info.backend,
                         task_info.shots, task_info.metadata)

        # Check if failed
        if task_info.status == TaskStatus.FAILED:
            if raise_on_failure:
                detail = task_info.error_message or "(no error message recorded)"
                raise TaskFailedError(
                    f"Task '{task_id}' failed on backend "
                    f"'{task_info.backend}': {detail}",
                    task_id=task_id,
                    backend=task_info.backend,
                    details={"error_message": task_info.error_message,
                             "metadata": task_info.metadata},
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
                    return _wrap(final_info.get("result"), backend,
                                 task_info.shots, task_info.metadata)

            raise TaskTimeoutError(
                f"Timeout waiting for task '{task_id}' to complete.",
                task_id=task_id,
                timeout=timeout,
            )

        # Wait before next poll
        time.sleep(poll_interval)


def poll_result(task_id: str) -> TaskInfo:
    """Non-blocking status check: return current task status/result without waiting.

    Unlike :func:`wait_for_result`, this returns immediately with the latest
    cached status. Call it in a loop if you want to poll without blocking.

    Args:
        task_id: The task identifier (``uqt_*`` or platform id).

    Returns:
        :class:`TaskInfo` with current status. Check ``.status`` for
        ``TaskStatus.SUCCESS``, ``TaskStatus.FAILED``, ``TaskStatus.RUNNING``,
        etc. If the task has completed, ``.result`` will be populated.

    Example:
        >>> task_id = submit_task(circuit, backend='originq:WK_C180')
        >>> while True:
        ...     info = poll_result(task_id)
        ...     if info.status in (TaskStatus.SUCCESS, TaskStatus.FAILED):
        ...         break
        ...     time.sleep(2)
    """
    return query_task(task_id)


def get_result(
    task_id: str,
    timeout: float = 300.0,
    poll_interval: float = 5.0,
    raise_on_failure: bool = True,
) -> UnifiedResult | list[UnifiedResult] | None:
    """Blocking retrieval: wait until task completes or timeout.

    This is a convenience alias for :func:`wait_for_result`. The name
    ``get_result`` emphasises the "I want the answer" pattern, while
    ``wait_for_result`` emphasises the blocking behaviour.

    Args:
        task_id: The task identifier.
        timeout: Maximum time to wait in seconds (default 300).
        poll_interval: Seconds between status checks (default 5).
        raise_on_failure: If True (default), raise ``TaskFailedError``
            when the task fails. If False, return ``None`` on failure.

    Returns:
        :class:`UnifiedResult` for single-circuit tasks, or
        ``list[UnifiedResult]`` for native batch submissions.
        Returns ``None`` if the task failed and *raise_on_failure* is False.

    Raises:
        TaskTimeoutError: If *timeout* is exceeded.
        TaskFailedError: If the task fails and *raise_on_failure* is True.
    """
    return wait_for_result(task_id, timeout, poll_interval, raise_on_failure)


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
        timeout: float = 300.0,
        poll_interval: float = 5.0,
        raise_on_failure: bool = True,
    ) -> UnifiedResult | list[UnifiedResult] | None:
        """Wait for a task to complete. See :func:`wait_for_result`."""
        return wait_for_result(
            task_id,
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
