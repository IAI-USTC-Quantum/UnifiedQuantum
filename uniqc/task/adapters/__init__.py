"""Quantum cloud backend adapters.

Each adapter provides a consistent interface (submit / query / translate)
for a specific quantum computing provider, encapsulating all network
communication within the adapter layer.
"""

from __future__ import annotations

__all__ = [
    "QuantumAdapter",
    "OriginQAdapter",
    "QuafuAdapter",
    "QiskitAdapter",
    "IBMAdapter",
    "DummyAdapter",
    # Constants (re-exported from base for convenience)
    "TASK_STATUS_FAILED",
    "TASK_STATUS_SUCCESS",
    "TASK_STATUS_RUNNING",
]

from uniqc.task.adapters.base import (
    TASK_STATUS_FAILED,
    TASK_STATUS_RUNNING,
    TASK_STATUS_SUCCESS,
    QuantumAdapter,
)
from uniqc.task.adapters.originq_adapter import OriginQAdapter
from uniqc.task.adapters.quafu_adapter import QuafuAdapter
from uniqc.task.adapters.qiskit_adapter import QiskitAdapter
from uniqc.task.adapters.ibm_adapter import IBMAdapter

# DummyAdapter requires simulation dependencies
# Import lazily to avoid errors when simulation deps not installed
try:
    from uniqc.task.adapters.dummy_adapter import DummyAdapter
except ImportError:
    DummyAdapter = None  # type: ignore[misc,assignment]
