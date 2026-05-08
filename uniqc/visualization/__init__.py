"""Circuit and result visualization helpers."""

from .result import plot_distribution, plot_histogram
from .timeline import (
    TimelineDurationError,
    TimelineGate,
    TimelineSchedule,
    circuit_to_html,
    create_time_line_table,
    format_result,
    plot_time_line,
    plot_time_line_html,
    schedule_circuit,
)

__all__ = [
    "TimelineDurationError",
    "TimelineGate",
    "TimelineSchedule",
    "circuit_to_html",
    "create_time_line_table",
    "draw",
    "draw_html",
    "format_result",
    "plot_distribution",
    "plot_histogram",
    "plot_time_line",
    "plot_time_line_html",
    "schedule_circuit",
]


def draw(*args, **kwargs):
    """Lazy import for circuit drawing to avoid importing optional dependencies."""
    from .circuit import draw as _draw

    return _draw(*args, **kwargs)


def draw_html(*args, **kwargs):
    """Lazy import for HTML circuit drawing to avoid importing optional dependencies."""
    from .circuit import draw_html as _draw_html

    return _draw_html(*args, **kwargs)
