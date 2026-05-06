from ._utils import CompilationFailedException as CompilationFailedException
from .compiler import CompilationResult as CompilationResult
from .compiler import TranspilerConfig as TranspilerConfig
from .compiler import compile as compile
from .converter import convert_oir_to_qasm as convert_oir_to_qasm
from .converter import convert_qasm_to_oir as convert_qasm_to_oir
from .policy import (
    PLATFORM_BASIS_GATES as PLATFORM_BASIS_GATES,
)
from .policy import (
    PLATFORM_SUBMIT_LANGUAGE as PLATFORM_SUBMIT_LANGUAGE,
)
from .policy import (
    compile_for_backend as compile_for_backend,
)
from .policy import (
    resolve_basis_gates as resolve_basis_gates,
)
from .policy import (
    resolve_submit_language as resolve_submit_language,
)
from .validation import (
    VIRTUAL_Z_GATES as VIRTUAL_Z_GATES,
)
from .validation import (
    CompatibilityReport as CompatibilityReport,
)
from .validation import (
    compatibility_report as compatibility_report,
)
from .validation import (
    compute_gate_depth as compute_gate_depth,
)
from .validation import (
    is_compatible as is_compatible,
)

try:
    from uniqc.visualization.timeline import (
        TimelineDurationError,
        TimelineGate,
        TimelineSchedule,
        circuit_to_html,
        plot_time_line,
        plot_time_line_html,
        schedule_circuit,
    )
except ImportError:
    TimelineDurationError = None
    TimelineGate = None
    TimelineSchedule = None
    circuit_to_html = None
    plot_time_line = None
    plot_time_line_html = None
    schedule_circuit = None


def draw(*args, **kwargs):
    """Lazy import for draw function to avoid hard dependency on pyqpanda3."""
    from uniqc.visualization.circuit import draw as _draw
    return _draw(*args, **kwargs)
