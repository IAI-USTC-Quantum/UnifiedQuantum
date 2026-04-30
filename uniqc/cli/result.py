"""Result query subcommand."""

from __future__ import annotations

import os
from typing import Optional

import typer

from .output import AI_HINTS_OPTION, build_ref_str, print_ai_hints
from .output import extract_counts_and_probs, format_prob, print_error, print_json, print_table

HELP = (
    "Query task results from quantum cloud platforms\n"
    f"  {build_ref_str('result')}"
)


def result(
    task_id: str = typer.Argument(..., help="Task ID to query"),
    platform: Optional[str] = typer.Option(None, "--platform", "-p", help="Platform: originq/quafu/ibm"),
    wait: bool = typer.Option(False, "--wait", "-w", help="Wait for task completion"),
    timeout: float = typer.Option(300.0, "--timeout", help="Timeout in seconds"),
    format: str = typer.Option("table", "--format", "-f", help="Output format: table/json"),
    ai_hints: bool = AI_HINTS_OPTION,
):
    """Query result of a submitted task.

    Workflow:
      - No result yet? Use --wait (or -w) to poll until task completes.
      - Task not found? Run uniqc task list to see all tasks and find the correct task_id.
      - To list all tasks: uniqc task list
      - Task is still pending/running? Increase --timeout if needed.
    """
    if ai_hints or os.environ.get("UNIQC_AI_HINTS"):
        print_ai_hints("result")

    show_result(task_id, platform=platform, wait=wait, timeout=timeout, format=format)


def show_result(
    task_id: str,
    platform: str | None = None,
    wait: bool = False,
    timeout: float = 300.0,
    format: str = "table",
) -> None:
    """Show task result."""
    try:
        if wait:
            result_data = _wait_for_result(task_id, platform, timeout)
        else:
            result_data = _query_result(task_id, platform)
    except Exception as e:
        print_error(str(e))
        raise typer.Exit(1)

    if result_data is None:
        print_error(f"No result available for task {task_id}")
        raise typer.Exit(1)

    if format == "json":
        print_json(result_data)
    else:
        _print_result_table(task_id, result_data)


def _query_result(task_id: str, platform: str | None) -> dict | None:
    """Query task result using the unified task_manager API."""
    from uniqc.task_manager import query_task

    task_info = query_task(task_id, backend=platform)
    if task_info and task_info.result:
        return task_info.result
    return None


def _wait_for_result(task_id: str, platform: str | None, timeout: float) -> dict | None:
    """Wait for task result."""
    from uniqc.task_manager import wait_for_result

    return wait_for_result(task_id, backend=platform, timeout=timeout)


def _print_result_table(task_id: str, result_data: dict | list) -> None:
    """Print result as a table, regardless of the adapter-specific shape."""
    counts, probs = extract_counts_and_probs(result_data)

    if not counts and not probs:
        print_table(
            f"Result for {task_id}",
            ["State", "Count", "Probability"],
            [],
        )
        return

    if counts:
        total = sum(counts.values()) or 1
        rows = [
            [
                state,
                str(count),
                format_prob(probs.get(state, count / total)),
            ]
            for state, count in sorted(counts.items(), key=lambda x: x[1], reverse=True)
        ]
    else:
        rows = [
            [state, "-", format_prob(prob)]
            for state, prob in sorted(probs.items(), key=lambda x: x[1], reverse=True)
        ]

    print_table(
        f"Result for {task_id}",
        ["State", "Count", "Probability"],
        rows,
    )
