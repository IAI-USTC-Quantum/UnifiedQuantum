from ._utils import CompilationFailedException as CompilationFailedException
from .compiler import CompilationResult as CompilationResult
from .compiler import TranspilerConfig as TranspilerConfig
from .compiler import compile as compile
from .converter import convert_oir_to_qasm as convert_oir_to_qasm
from .converter import convert_qasm_to_oir as convert_qasm_to_oir

try:
    from uniqc.visualization.timeline import plot_time_line
except ImportError:
    plot_time_line = None


def draw(*args, **kwargs):
    """Lazy import for draw function to avoid hard dependency on pyqpanda3."""
    from uniqc.visualization.circuit import draw as _draw
    return _draw(*args, **kwargs)
