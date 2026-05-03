"""Backend adapter layer.

This package owns cloud backend configuration, backend discovery, circuit
input/output adapters, task submission/querying, and the local dummy backend.
"""

from .backend import (
    BACKENDS,
    DummyBackend,
    IBMBackend,
    OriginQBackend,
    QuantumBackend,
    QuafuBackend,
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
    QuafuCircuitAdapter,
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
