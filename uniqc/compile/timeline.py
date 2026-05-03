"""Compatibility wrapper for timeline visualization."""

from uniqc.visualization.timeline import (
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
    "format_result",
    "plot_time_line",
    "plot_time_line_html",
    "schedule_circuit",
]
