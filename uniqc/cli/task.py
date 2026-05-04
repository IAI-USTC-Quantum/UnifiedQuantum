"""Task management subcommand."""

from __future__ import annotations

from typing import Optional

import typer

from .output import (
    AI_HINTS_OPTION,
    ai_hints_enabled,
    build_ref_str,
    console,
    extract_counts_and_probs,
    format_prob,
    print_ai_hints,
    print_error,
    print_info,
    print_json,
    print_success,
    print_table,
)

app = typer.Typer(
    help=(
        "Manage submitted tasks\n"
        f"  {build_ref_str('task-list')}"
    ),
)


@app.command("list")
def list_tasks(
    status: Optional[str] = typer.Option(None, "--status", help="Filter by status: pending/running/success/failed"),
    platform: Optional[str] = typer.Option(None, "--platform", "-p", help="Filter by platform"),
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum number of tasks to show"),
    format: str = typer.Option("table", "--format", "-f", help="Output format: table/json"),
    ai_hints: bool = AI_HINTS_OPTION,
):
    """List submitted tasks.

    Workflow:
      - No tasks shown? Configure your platform: uniqc config set originq.token <TOKEN>
      - Then validate: uniqc config validate
      - Wrong platform? Filter: uniqc task list --platform originq
      - Get a result: uniqc result <TASK_ID>
    """
    if ai_hints_enabled(ai_hints):
        print_ai_hints("task-list")

    from uniqc.backend_adapter.task_manager import list_tasks as _list_tasks

    tasks = _list_tasks(status=status, backend=platform)

    if not tasks:
        print_info("No tasks found")
        return

    tasks = tasks[:limit]

    if format == "json":
        print_json([task_to_dict(t) for t in tasks])
    else:
        rows = []
        for task in tasks:
            rows.append(
                [
                    task.task_id,
                    task.backend,
                    task.status,
                    str(task.shots),
                    task.submit_time[:19] if task.submit_time else "N/A",
                ]
            )
        print_table("Tasks", ["Task ID", "Platform", "Status", "Shots", "Submit Time"], rows)


@app.command()
def show(
    task_id: str = typer.Argument(..., help="Task ID to show"),
    format: str = typer.Option("table", "--format", "-f", help="Output format: table/json"),
    ai_hints: bool = AI_HINTS_OPTION,
):
    """Show details of a specific task.

    Workflow:
      - Get the measurement result: uniqc result <TASK_ID>
      - Task still running? Use uniqc result <TASK_ID> --wait to poll.
      - See all tasks: uniqc task list
    """
    if ai_hints_enabled(ai_hints):
        print_ai_hints("task-show")

    from uniqc.backend_adapter.task_manager import get_task, query_task

    task_info = get_task(task_id)

    if not task_info:
        task_info = query_task(task_id)

    if not task_info:
        print_error(f"Task {task_id} not found")
        raise typer.Exit(1)

    if format == "json":
        print_json(task_to_dict(task_info))
    else:
        print_table(
            f"Task {task_id}",
            ["Property", "Value"],
            [
                ["Task ID", task_info.task_id],
                ["Backend", task_info.backend],
                ["Status", task_info.status],
                ["Shots", str(task_info.shots)],
                ["Submit Time", task_info.submit_time or "N/A"],
                ["Update Time", task_info.update_time or "N/A"],
            ],
        )

        if task_info.result:
            console.print("\n[bold]Results:[/bold]")
            counts, probs = extract_counts_and_probs(
                task_info.result, shots=task_info.shots
            )
            # Prefer counts order for display; fall back to probabilities.
            if counts:
                rows = [
                    [
                        state,
                        str(count),
                        format_prob(probs.get(state, count / (sum(counts.values()) or 1))),
                    ]
                    for state, count in sorted(
                        counts.items(), key=lambda x: x[1], reverse=True
                    )
                ]
            else:
                rows = [
                    [state, "-", format_prob(prob)]
                    for state, prob in sorted(
                        probs.items(), key=lambda x: x[1], reverse=True
                    )
                ]
            print_table(
                "Measurement Results", ["State", "Count", "Probability"], rows
            )


@app.command()
def clear(
    status: Optional[str] = typer.Option(None, "--status", help="Clear tasks with this status"),
    force: bool = typer.Option(False, "--force", help="Force clear without confirmation"),
    ai_hints: bool = AI_HINTS_OPTION,
):
    """Clear completed or failed tasks from cache."""
    if ai_hints_enabled(ai_hints):
        print_ai_hints("task-list")

    from uniqc.backend_adapter.task_manager import clear_completed_tasks, clear_cache, list_tasks

    if status:
        count = clear_completed_tasks()
    else:
        if not force:
            confirm = typer.confirm("Clear all cached tasks?")
            if not confirm:
                print_info("Cancelled")
                return
        count = len(list_tasks())
        clear_cache()

    print_success(f"Cleared {count} tasks from cache")


def task_to_dict(task_info) -> dict:
    """Convert TaskInfo to dictionary."""
    return {
        "task_id": task_info.task_id,
        "backend": task_info.backend,
        "status": task_info.status,
        "shots": task_info.shots,
        "submit_time": task_info.submit_time,
        "update_time": task_info.update_time,
        "result": task_info.result,
        "metadata": task_info.metadata,
    }
