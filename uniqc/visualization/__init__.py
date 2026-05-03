"""Circuit and result visualization helpers."""

from .result import plot_distribution, plot_histogram
from .timeline import create_time_line_table, format_result, plot_time_line

__all__ = [
    "create_time_line_table",
    "format_result",
    "plot_distribution",
    "plot_histogram",
    "plot_time_line",
]


def draw(*args, **kwargs):
    """Lazy import for circuit drawing to avoid importing optional dependencies."""
    from .circuit import draw as _draw

    return _draw(*args, **kwargs)
