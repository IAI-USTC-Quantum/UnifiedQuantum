"""UnifiedQuantum public API.

The common user path is intentionally flat: frequently used classes and
functions can be imported directly from ``uniqc``.
"""

import warnings

from .backend_adapter.backend import (
    DummyBackend,
    IBMBackend,
    OriginQBackend,
    QuantumBackend,
    QuafuBackend,
    QuarkBackend,
    get_backend,
    list_backends,
    list_backends_by_platform,
)
from .backend_adapter.backend_info import BackendInfo, Platform, QubitTopology
from .backend_adapter.backend_registry import (
    BackendAuditIssue,
    audit_backend_info,
    audit_backends,
    fetch_all_backends,
    fetch_platform_backends,
    find_backend,
)
from .backend_adapter.circuit_adapter import (
    CircuitAdapter,
    IBMCircuitAdapter,
    OriginQCircuitAdapter,
    QuafuCircuitAdapter,
    QuarkCircuitAdapter,
)
from .backend_adapter.network_utils import (
    check_proxy_connectivity,
    detect_system_proxy,
    get_ibm_proxy_from_config,
    test_ibm_connectivity,
)
from .backend_adapter.region_selector import ChainSearchResult, RegionSearchResult, RegionSelector
from .backend_adapter.task.normalizers import normalize_dummy, normalize_ibm, normalize_originq, normalize_quafu
from .backend_adapter.task.options import (
    BackendOptions,
    BackendOptionsError,
    BackendOptionsFactory,
    DummyOptions,
    IBMOptions,
    OriginQOptions,
    QuafuOptions,
    QuarkOptions,
)
from .backend_adapter.task.result_types import UnifiedResult
from .backend_adapter.task.store import TaskStatus
from .backend_adapter.task_manager import (
    TaskInfo,
    TaskManager,
    clear_cache,
    clear_completed_tasks,
    dry_run_task,
    get_task,
    list_tasks,
    query_task,
    save_task,
    submit_batch,
    submit_task,
    wait_for_result,
)
from .calibration import (
    ReadoutCalibrationResult,
    XEBResult,
    find_cached_results,
    load_calibration_result,
    save_calibration_result,
)
from .algorithms.core.ansatz import hea, qaoa_ansatz, uccsd_ansatz
from .algorithms.core.circuits import (
    amplitude_estimation_circuit,
    amplitude_estimation_result,
    cluster_state,
    deutsch_jozsa_circuit,
    deutsch_jozsa_oracle,
    dicke_state_circuit,
    ghz_state,
    grover_diffusion,
    grover_operator,
    grover_oracle,
    qft_circuit,
    thermal_state_circuit,
    vqd_ansatz,
    vqd_circuit,
    vqd_overlap_circuit,
    w_state,
)
from .algorithms.core.measurement import (
    basis_rotation_measurement,
    BasisRotationMeasurement,
    classical_shadow,
    ClassicalShadow,
    pauli_expectation,
    PauliExpectation,
    shadow_expectation,
    state_tomography,
    StateTomography,
    tomography_summary,
)
from .algorithms.core.state_preparation import (
    basis_state,
    dicke_state,
    hadamard_superposition,
    rotation_prepare,
    thermal_state,
)
from .algorithms.workflows import readout_em_workflow, xeb_workflow
from .circuit_builder import Circuit, NamedCircuit, Parameter, Parameters, QReg, QRegSlice, Qubit, circuit_def, get_matrix
from .compile import CompilationFailedError, CompilationResult, TranspilerConfig, compile
from .compile.policy import compile_for_backend, resolve_basis_gates, resolve_submit_language
from .compile.validation import (
    VIRTUAL_Z_GATES,
    CompatibilityReport,
    compatibility_report,
    compute_gate_depth,
    is_compatible,
)
from .compile.originir import OriginIR_BaseParser
from .compile.qasm import OpenQASM2_BaseParser
from .exceptions import (
    AuthenticationError,
    BackendError,
    BackendNotAvailableError,
    BackendNotFoundError,
    BackendOptionsError,
    CircuitError,
    CircuitTranslationError,
    CompilationFailedError,
    ConfigError,
    ConfigValidationError,
    InsufficientCreditsError,
    MissingDependencyError,
    NetworkError,
    NotMatrixableError,
    NotSupportedGateError,
    PlatformNotFoundError,
    ProfileNotFoundError,
    QuotaExceededError,
    RegisterDefinitionError,
    RegisterNotFoundError,
    RegisterOutOfRangeError,
    StaleCalibrationError,
    TaskFailedError,
    TaskNotFoundError,
    TaskTimeoutError,
    TimelineDurationError,
    TopologyError,
    UnifiedQuantumError,
    UnsupportedGateError,
)
from .qem import M3Mitigator, ReadoutEM, StaleCalibrationError
from .utils import (
    calculate_exp_X,
    calculate_exp_Y,
    calculate_expectation,
    calculate_multi_basis_expectation,
    kv2list,
    list2kv,
    shots2prob,
)

try:
    from .simulator import OriginIR_Simulator
except ImportError:
    OriginIR_Simulator = None  # type: ignore[assignment]

try:
    import uniqc_cpp  # noqa: F401
except ImportError:
    warnings.warn("uniqc is not installed with UniqcCpp.", stacklevel=2)

try:
    from .visualization import circuit_to_html, plot_time_line, plot_time_line_html, schedule_circuit
except ImportError:
    circuit_to_html = None  # type: ignore[assignment]
    plot_time_line = None  # type: ignore[assignment]
    plot_time_line_html = None  # type: ignore[assignment]
    schedule_circuit = None  # type: ignore[assignment]

try:
    from ._version import __version__
except ImportError:
    __version__ = "0.0.0+unknown"

from . import algorithms, calibration, qem  # noqa: E402,F401
from . import config

_LAZY_EXPORTS = {
    "QuantumLayer": ("uniqc.torch_adapter", "QuantumLayer"),
    "TorchQuantumLayer": ("uniqc.torch_adapter", "TorchQuantumLayer"),
    "HybridQCLModel": ("uniqc.algorithms.core.training.hybrid_model", "HybridQCLModel"),
    "QAOASolver": ("uniqc.algorithms.core.training.qaoa_torch", "QAOASolver"),
    "QCNNClassifier": ("uniqc.algorithms.core.training.qcnn", "QCNNClassifier"),
    "QNNClassifier": ("uniqc.algorithms.core.training.qnn", "QNNClassifier"),
    "VQESolver": ("uniqc.algorithms.core.training.vqe_torch", "VQESolver"),
    "batch_execute": ("uniqc.torch_adapter", "batch_execute"),
    "batch_execute_with_params": ("uniqc.torch_adapter", "batch_execute_with_params"),
    "build_h2_hamiltonian": ("uniqc.algorithms.core.training.vqe_torch", "build_h2_hamiltonian"),
    "compute_all_gradients": ("uniqc.torch_adapter", "compute_all_gradients"),
    "parameter_shift_gradient": ("uniqc.torch_adapter", "parameter_shift_gradient"),
}


def __getattr__(name: str):
    if name in _LAZY_EXPORTS:
        module_name, attr_name = _LAZY_EXPORTS[name]
        module = __import__(module_name, fromlist=[attr_name])
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AuthenticationError",
    "BackendError",
    "BackendAuditIssue",
    "BackendInfo",
    "BackendNotAvailableError",
    "BackendNotFoundError",
    "BackendOptions",
    "BackendOptionsError",
    "BackendOptionsFactory",
    "ChainSearchResult",
    "Circuit",
    "CircuitAdapter",
    "CircuitError",
    "CircuitTranslationError",
    "CompatibilityReport",
    "CompilationFailedError",
    "ConfigError",
    "ConfigValidationError",
    "CompilationResult",
    "DummyBackend",
    "DummyOptions",
    "IBMCircuitAdapter",
    "IBMBackend",
    "IBMOptions",
    "HybridQCLModel",
    "InsufficientCreditsError",
    "M3Mitigator",
    "MissingDependencyError",
    "NamedCircuit",
    "NetworkError",
    "NotMatrixableError",
    "NotSupportedGateError",
    "OpenQASM2_BaseParser",
    "OriginIR_BaseParser",
    "OriginIR_Simulator",
    "OriginQCircuitAdapter",
    "OriginQBackend",
    "OriginQOptions",
    "Parameter",
    "Parameters",
    "Platform",
    "PlatformNotFoundError",
    "ProfileNotFoundError",
    "QuantumBackend",
    "QuantumLayer",
    "QAOASolver",
    "QCNNClassifier",
    "QNNClassifier",
    "QReg",
    "QRegSlice",
    "Qubit",
    "QubitTopology",
    "QuotaExceededError",
    "QuafuBackend",
    "QuafuCircuitAdapter",
    "QuafuOptions",
    "QuarkBackend",
    "QuarkCircuitAdapter",
    "QuarkOptions",
    "ReadoutCalibrationResult",
    "RegisterDefinitionError",
    "RegisterNotFoundError",
    "RegisterOutOfRangeError",
    "ReadoutEM",
    "RegionSearchResult",
    "RegionSelector",
    "StaleCalibrationError",
    "TaskFailedError",
    "TaskInfo",
    "TaskManager",
    "TaskNotFoundError",
    "TaskStatus",
    "TaskTimeoutError",
    "TimelineDurationError",
    "TopologyError",
    "TorchQuantumLayer",
    "TranspilerConfig",
    "UnifiedQuantumError",
    "UnifiedResult",
    "UnsupportedGateError",
    "VQESolver",
    "XEBResult",
    "__version__",
    "amplitude_estimation_circuit",
    "amplitude_estimation_result",
    "algorithms",
    "audit_backend_info",
    "audit_backends",
    "basis_rotation_measurement",
    "BasisRotationMeasurement",
    "basis_state",
    "batch_execute",
    "batch_execute_with_params",
    "build_h2_hamiltonian",
    "calibration",
    "calculate_exp_X",
    "calculate_exp_Y",
    "calculate_expectation",
    "calculate_multi_basis_expectation",
    "check_proxy_connectivity",
    "circuit_to_html",
    "circuit_def",
    "classical_shadow",
    "ClassicalShadow",
    "clear_cache",
    "clear_completed_tasks",
    "cluster_state",
    "compute_all_gradients",
    "compile",
    "compile_for_backend",
    "compatibility_report",
    "compute_gate_depth",
    "config",
    "deutsch_jozsa_circuit",
    "deutsch_jozsa_oracle",
    "detect_system_proxy",
    "dicke_state",
    "dicke_state_circuit",
    "dry_run_task",
    "fetch_all_backends",
    "fetch_platform_backends",
    "find_cached_results",
    "find_backend",
    "get_backend",
    "get_ibm_proxy_from_config",
    "get_matrix",
    "get_task",
    "ghz_state",
    "grover_diffusion",
    "grover_operator",
    "grover_oracle",
    "hadamard_superposition",
    "hea",
    "is_compatible",
    "kv2list",
    "list_backends",
    "list_backends_by_platform",
    "list2kv",
    "list_tasks",
    "load_calibration_result",
    "normalize_dummy",
    "normalize_ibm",
    "normalize_originq",
    "normalize_quafu",
    "parameter_shift_gradient",
    "pauli_expectation",
    "PauliExpectation",
    "plot_time_line",
    "plot_time_line_html",
    "qaoa_ansatz",
    "qem",
    "qft_circuit",
    "query_task",
    "readout_em_workflow",
    "rotation_prepare",
    "save_calibration_result",
    "save_task",
    "shadow_expectation",
    "shots2prob",
    "schedule_circuit",
    "state_tomography",
    "StateTomography",
    "submit_batch",
    "submit_task",
    "test_ibm_connectivity",
    "thermal_state",
    "thermal_state_circuit",
    "tomography_summary",
    "uccsd_ansatz",
    "resolve_basis_gates",
    "resolve_submit_language",
    "VIRTUAL_Z_GATES",
    "vqd_ansatz",
    "vqd_circuit",
    "vqd_overlap_circuit",
    "wait_for_result",
    "w_state",
    "xeb_workflow",
]
