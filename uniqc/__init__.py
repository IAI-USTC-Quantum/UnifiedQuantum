from pathlib import Path

from . import config
from .circuit_builder import Circuit
from .originir import OriginIR_BaseParser
from .qasm import OpenQASM2_BaseParser
try:
    from .simulator import OriginIR_Simulator
except:
    # warning has been omitted in the submodule.
    pass
try:
    import uniqc_cpp
except ImportError:
    import warnings
    warnings.warn('uniqc is not installed with UniqcCpp.')

# Analyzer exports
from .analyzer import (
    calculate_expectation,
    calculate_exp_X,
    calculate_exp_Y,
    calculate_multi_basis_expectation,
    shots2prob,
    kv2list,
    list2kv,
)

# Unified result types and normalizers
from .task.normalizers import normalize_originq, normalize_quafu, normalize_ibm, normalize_dummy
from .task.result_types import UnifiedResult

# Optional import - requires visualization dependencies (pandas, matplotlib)
try:
    from .transpiler import plot_time_line
except ImportError:
    pass

from .circuit_adapter import (
    CircuitAdapter,
    OriginQCircuitAdapter,
    QuafuCircuitAdapter,
    IBMCircuitAdapter,
)

from .exceptions import (
    UnifiedQuantumError,
    AuthenticationError,
    InsufficientCreditsError,
    QuotaExceededError,
    NetworkError,
    TaskFailedError,
    TaskTimeoutError,
    TaskNotFoundError,
    BackendError,
    BackendNotAvailableError,
    BackendNotFoundError,
    CircuitError,
    CircuitTranslationError,
    UnsupportedGateError,
)

from .task_manager import (
    submit_task,
    submit_batch,
    query_task,
    wait_for_result,
    save_task,
    get_task,
    list_tasks,
    clear_completed_tasks,
    clear_cache,
    TaskInfo,
    TaskManager,
)

# Enhanced transpiler
from .transpiler.compiler import (  # noqa: F401
    compile,
    TranspilerConfig,
    CompilationResult,
    CompilationFailedException,
)

# Unified backend options
from .task.options import (  # noqa: F401
    BackendOptions,
    OriginQOptions,
    QuafuOptions,
    IBMOptions,
    DummyOptions,
    BackendOptionsFactory,
    BackendOptionsError,
)

# Region selector
from .region_selector import RegionSelector, ChainSearchResult, RegionSearchResult  # noqa: F401

from .network_utils import (
    check_proxy_connectivity,
    detect_system_proxy,
    test_ibm_connectivity,
    get_ibm_proxy_from_config,
)

from .version import __version__
