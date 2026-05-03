"""Quantum cloud backend adapters.

Each adapter provides a consistent interface (submit / query / translate / dry_run)
for a specific quantum computing provider, encapsulating all network
communication within the adapter layer.

Each adapter implements ``dry_run(originir, shots, **kwargs)`` for offline
validation without any cloud API calls. See ``uniqc.backend_adapter.task_manager.dry_run_task``
for the high-level API.

Note:
    Any dry-run success followed by actual submission failure is a critical bug.
    Please report it at the UnifiedQuantum issue tracker.
"""

from __future__ import annotations

__all__ = [
    "QuantumAdapter",
    "DryRunResult",
    "OriginQAdapter",
    "BackendUnavailableError",
    "QuafuAdapter",
    "QiskitAdapter",
    "IBMAdapter",
    "DummyAdapter",
    # Constants (re-exported from base for convenience)
    "TASK_STATUS_FAILED",
    "TASK_STATUS_SUCCESS",
    "TASK_STATUS_RUNNING",
]

from uniqc.backend_adapter.task.adapters.base import (
    TASK_STATUS_FAILED,
    TASK_STATUS_RUNNING,
    TASK_STATUS_SUCCESS,
    DryRunResult,
    QuantumAdapter,
)
from uniqc.backend_adapter.task.adapters.ibm_adapter import IBMAdapter
from uniqc.backend_adapter.task.adapters.originq_adapter import BackendUnavailableError, OriginQAdapter
from uniqc.backend_adapter.task.adapters.qiskit_adapter import QiskitAdapter
from uniqc.backend_adapter.task.adapters.quafu_adapter import QuafuAdapter

# DummyAdapter requires simulation dependencies
# Import lazily to avoid errors when simulation deps not installed
try:
    from uniqc.backend_adapter.task.adapters.dummy_adapter import DummyAdapter
except ImportError:
    DummyAdapter = None  # type: ignore[misc,assignment]
