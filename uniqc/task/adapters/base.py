"""Base adapter interface for quantum cloud backends.

Every backend adapter must implement this interface, providing:
1. Translation from OriginIR string to the provider's native circuit type.
2. Task submission via the provider's Python SDK (not raw REST).
3. Task status query and result retrieval.
4. Dry-run validation without making any network calls.

The adapter layer replaces all direct ``requests`` REST calls within the
task modules.  Each adapter is a stateful object that holds the provider
session / client and configuration.

Dry-run Validation
------------------
Every adapter implements ``dry_run(originir, shots, **kwargs)`` to validate
a circuit offline before submission. This checks:
  1. OriginIR parses without error.
  2. All gates are supported by the target backend.
  3. Qubit count fits within the backend's limits.
  4. The native circuit object is structurally valid.

No cloud API calls are made. A dry-run success followed by actual submission
failure is a critical bug — please report it at the issue tracker.
"""

from __future__ import annotations

__all__ = [
    "QuantumAdapter",
    "DryRunResult",
    "TASK_STATUS_FAILED",
    "TASK_STATUS_SUCCESS",
    "TASK_STATUS_RUNNING",
    "_dry_run_success",
    "_dry_run_failed",
]

import abc
from typing import TYPE_CHECKING, Any

from uniqc.task.result_types import DryRunResult

if TYPE_CHECKING:
    pass


TASK_STATUS_FAILED = "failed"
TASK_STATUS_SUCCESS = "success"
TASK_STATUS_RUNNING = "running"


def _dry_run_failed(
    error_message: str,
    *,
    details: str,
    backend_name: str | None = None,
    warnings: tuple[str, ...] = (),
) -> DryRunResult:
    """Build a failure DryRunResult from a caught exception."""
    return DryRunResult(
        success=False,
        details=details,
        error=error_message,
        warnings=warnings,
        backend_name=backend_name,
    )


def _dry_run_success(
    details: str,
    *,
    backend_name: str | None = None,
    circuit_qubits: int | None = None,
    supported_gates: tuple[str, ...] = (),
    warnings: tuple[str, ...] = (),
) -> DryRunResult:
    """Build a success DryRunResult."""
    return DryRunResult(
        success=True,
        details=details,
        backend_name=backend_name,
        circuit_qubits=circuit_qubits,
        supported_gates=supported_gates,
        warnings=warnings,
    )


class QuantumAdapter(abc.ABC):
    """Abstract base class for quantum cloud backend adapters.

    Subclass this for each backend (originq_cloud, quafu, ibm, ...).
    Each adapter is instantiated once per task module and reused.
    """

    name: str = "base"

    # -------------------------------------------------------------------------
    # Circuit translation
    # -------------------------------------------------------------------------

    @abc.abstractmethod
    def translate_circuit(self, originir: str) -> Any:
        """Translate an OriginIR circuit string to the provider's native circuit type.

        Args:
            originir: Circuit in OriginIR format.

        Returns:
            Provider-specific circuit object.
        """
        ...

    # -------------------------------------------------------------------------
    # Task submission
    # -------------------------------------------------------------------------

    @abc.abstractmethod
    def submit(self, circuit: Any, *, shots: int = 1000, **kwargs: Any) -> str:
        """Submit a circuit to the backend and return a task ID.

        Args:
            circuit: Provider-native circuit object (result of ``translate_circuit``).
            shots: Number of measurement shots.
            **kwargs: Additional provider-specific parameters
                (e.g. chip_id, auto_mapping, circuit_optimize).

        Returns:
            str: Task ID assigned by the backend.
        """
        ...

    @abc.abstractmethod
    def submit_batch(self, circuits: list[Any], *, shots: int = 1000, **kwargs: Any) -> list[str]:
        """Submit multiple circuits as a single batch.

        Args:
            circuits: List of provider-native circuit objects.
            shots: Number of measurement shots.
            **kwargs: Additional provider-specific parameters.

        Returns:
            list[str]: Task IDs (one per circuit), or a single task ID
            if the backend returns a group ID.
        """
        ...

    # -------------------------------------------------------------------------
    # Task query
    # -------------------------------------------------------------------------

    @abc.abstractmethod
    def query(self, taskid: str) -> dict[str, Any]:
        """Query a single task's status and result.

        Args:
            taskid: Task identifier.

        Returns:
            dict with keys:
                - ``status``: ``'success'`` | ``'failed'`` | ``'running'``
                - ``result``: execution result (present when status is ``'success'``
                  or ``'failed'``)
        """
        ...

    @abc.abstractmethod
    def query_batch(self, taskids: list[str]) -> dict[str, Any]:
        """Query multiple tasks' status and merge results.

        Overall status is the worst case:
        ``'failed'`` > ``'running'`` > ``'success'``.

        Args:
            taskids: List of task identifiers.

        Returns:
            dict with keys: ``status``, ``result`` (list of results).
        """
        ...

    # -------------------------------------------------------------------------
    # Utils
    # -------------------------------------------------------------------------

    def is_available(self) -> bool:
        """Return True if the required packages / credentials are configured.

        Defaults to ``False`` so that subclasses must explicitly opt-in,
        avoiding the risk of an unconfigured adapter incorrectly reporting
        availability.
        """
        return False

    def list_backends(self) -> list[dict[str, Any]]:
        """Return raw backend metadata from the platform API.

        Returns a list of dicts with at least a ``"name"`` key.
        The dict shape is platform-specific; the caller is responsible for
        normalising the data into ``BackendInfo`` objects.

        Raises:
            Exception: If the platform API call fails (auth error, network
                error, etc.).  Subclasses should propagate the original
                exception type so callers can distinguish auth failures from
                network failures.
        """
        raise NotImplementedError(f"{self.__class__.__name__} does not implement list_backends")

    # -------------------------------------------------------------------------
    # Dry-run validation
    # -------------------------------------------------------------------------

    def dry_run(self, originir: str, *, shots: int = 1000, **kwargs: Any) -> DryRunResult:
        """Validate a circuit without making network calls.

        Subclasses must implement this method. The default implementation
        raises NotImplementedError.

        Validation checklist (where determinable offline):
        1. OriginIR parses without error.
        2. All gates are supported by the target backend.
        3. Qubit count fits within the backend's limits.
        4. The native circuit object is structurally valid.

        This method must NOT make any cloud API calls. All checks must be
        local-only.

        Args:
            originir: Circuit in OriginIR format.
            shots: Number of measurement shots (for shots-limit validation).
            **kwargs: Adapter-specific options (e.g. chip_id for IBM/Quafu).

        Returns:
            DryRunResult with success=True/False, details, warnings, and metadata.

        Raises:
            NotImplementedError: Subclasses must implement this method.

        Note:
            Any dry-run success followed by actual submission failure is a
            critical bug. Please report it at the UnifiedQuantum issue tracker.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement dry_run(). "
            "Subclasses of QuantumAdapter must implement dry_run()."
        )
