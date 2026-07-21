"""Backend adapter layer.

This package owns cloud backend configuration, backend discovery, circuit
input/output adapters, task submission/querying, and the local dummy backend.
"""

from importlib import import_module

from .backend import (
    BACKENDS,
    DummyBackend,
    IBMBackend,
    OriginQBackend,
    QuantumBackend,
    QuarkBackend,
    get_backend,
    list_backends,
)
from .backend_info import BackendInfo, Platform, QubitTopology
from .backend_registry import (
    BackendAuditIssue,
    audit_backend_info,
    audit_backends,
    fetch_all_backends,
    fetch_platform_backends,
    find_backend,
)
from .circuit_adapter import (
    CircuitAdapter,
    IBMCircuitAdapter,
    OriginQCircuitAdapter,
    QuarkCircuitAdapter,
)
from .region_selector import ChainSearchResult, RegionSearchResult, RegionSelector
from .task_manager import (
    TaskInfo,
    TaskManager,
    clear_cache,
    clear_completed_tasks,
    get_task,
    list_tasks,
    query_task,
    save_task,
    submit_batch,
    submit_task,
    wait_for_result,
)

__all__ = [
    "BACKENDS",
    "BackendAuditIssue",
    "BackendInfo",
    "ChainSearchResult",
    "CircuitAdapter",
    "DummyBackend",
    "IBMBackend",
    "IBMCircuitAdapter",
    "OriginQBackend",
    "OriginQCircuitAdapter",
    "Platform",
    "QuantumBackend",
    "QubitTopology",
    "QuafuBackend",
    "QuafuCircuitAdapter",
    "QuarkBackend",
    "QuarkCircuitAdapter",
    "RegionSearchResult",
    "RegionSelector",
    "TaskInfo",
    "TaskManager",
    "audit_backend_info",
    "audit_backends",
    "clear_cache",
    "clear_completed_tasks",
    "fetch_all_backends",
    "fetch_platform_backends",
    "find_backend",
    "get_backend",
    "get_task",
    "list_backends",
    "list_tasks",
    "query_task",
    "save_task",
    "submit_batch",
    "submit_task",
    "wait_for_result",
]

_LAZY_EXPORTS = {
    "QuafuBackend": ("uniqc.backend_adapter.backend", "QuafuBackend"),
    "QuafuCircuitAdapter": ("uniqc.backend_adapter.circuit_adapter", "QuafuCircuitAdapter"),
}


def __getattr__(name: str):
    if name in _LAZY_EXPORTS:
        module_name, attr_name = _LAZY_EXPORTS[name]
        value = getattr(import_module(module_name), attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
