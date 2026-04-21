"""Cloud task submission subcommand."""

from __future__ import annotations

from pathlib import Path

import typer

from .output import print_error, print_json, print_success, print_table

HELP = "Submit circuits to quantum cloud platforms"
INPUT_FILES_ARGUMENT = typer.Argument(..., help="Circuit file(s) to submit", exists=True)
PLATFORM_OPTION = typer.Option(..., "--platform", "-p", help="Platform: originq/quafu/ibm/dummy")
BACKEND_OPTION = typer.Option(None, "--backend", "-b", help="Backend name (e.g., 'origin:wuyuan:d5' for OriginQ)")
SHOTS_OPTION = typer.Option(1000, "--shots", "-s", help="Number of measurement shots")
NAME_OPTION = typer.Option(None, "--name", help="Task name")
WAIT_OPTION = typer.Option(False, "--wait", "-w", help="Wait for result after submission")
TIMEOUT_OPTION = typer.Option(300.0, "--timeout", help="Timeout in seconds when waiting")
FORMAT_OPTION = typer.Option("table", "--format", "-f", help="Output format: table/json")


def submit(
    input_files: list[Path] = INPUT_FILES_ARGUMENT,
    platform: str = PLATFORM_OPTION,
    backend: str | None = BACKEND_OPTION,
    shots: int = SHOTS_OPTION,
    name: str | None = NAME_OPTION,
    wait: bool = WAIT_OPTION,
    timeout: float = TIMEOUT_OPTION,
    format: str = FORMAT_OPTION,
):
    """Submit circuit(s) to a quantum cloud platform."""
    if platform not in ("originq", "quafu", "ibm", "dummy"):
        print_error(f"Unknown platform: {platform}. Use originq/quafu/ibm/dummy.")
        raise typer.Exit(1)

    circuits = []
    for path in input_files:
        circuits.append(path.read_text(encoding="utf-8"))

    try:
        if len(circuits) == 1:
            task_id = _submit_single(circuits[0], platform, backend, shots, name)
            if format == "json":
                print_json({"task_id": task_id, "platform": platform, "shots": shots})
            else:
                print_success(f"Task submitted: {task_id}")
        else:
            task_ids = _submit_batch(circuits, platform, backend, shots, name)
            if format == "json":
                print_json({"task_ids": task_ids, "platform": platform, "shots": shots})
            else:
                print_table(
                    "Submitted Tasks",
                    ["#", "Task ID"],
                    [[str(i + 1), tid] for i, tid in enumerate(task_ids)],
                )
    except Exception as e:
        print_error(str(e))
        raise typer.Exit(1) from e

    if wait and len(circuits) == 1:
        _wait_and_show(task_id, platform, timeout, format)


def _parse_to_circuit(circuit_text: str):
    """Parse OriginIR or OpenQASM 2.0 text into a ``Circuit`` object."""
    from uniqc.originir import OriginIR_BaseParser

    parser = OriginIR_BaseParser()
    try:
        parser.parse(circuit_text)
        return parser.to_circuit()
    except Exception:
        # Fall back to QASM
        from uniqc.qasm import OpenQASM2_BaseParser

        qasm_parser = OpenQASM2_BaseParser()
        qasm_parser.parse(circuit_text)
        return qasm_parser.to_circuit()


def _submit_single(circuit: str, platform: str, backend_name: str | None, shots: int, name: str | None) -> str:
    """Submit a single circuit using the unified task_manager API."""
    from uniqc.task_manager import submit_task

    parsed_circuit = _parse_to_circuit(circuit)

    # Build kwargs for backend-specific options
    kwargs: dict = {"shots": shots}
    if backend_name:
        kwargs["backend_name"] = backend_name
    if name:
        kwargs["metadata"] = {"task_name": name}

    # Use dummy mode if platform is 'dummy'
    dummy = platform == "dummy"
    backend = "originq" if dummy else platform

    return submit_task(parsed_circuit, backend=backend, dummy=dummy, **kwargs)


def _submit_batch(circuits: list[str], platform: str, backend_name: str | None, shots: int, name: str | None) -> list[str]:
    """Submit multiple circuits using the unified task_manager API."""
    from uniqc.task_manager import submit_batch

    from .output import print_warning

    if name:
        print_warning("Task name is not supported for batch submissions yet. Ignoring --name option.")

    parsed_circuits = [_parse_to_circuit(c) for c in circuits]

    # Build kwargs for backend-specific options
    kwargs: dict = {"shots": shots}
    if backend_name:
        kwargs["backend_name"] = backend_name

    # Use dummy mode if platform is 'dummy'
    dummy = platform == "dummy"
    backend = "originq" if dummy else platform

    return submit_batch(parsed_circuits, backend=backend, dummy=dummy, **kwargs)


def _wait_and_show(task_id: str, platform: str, timeout: float, format: str) -> None:
    """Wait for task result and display it."""
    from .result import show_result

    show_result(task_id, platform=platform, wait=True, timeout=timeout, format=format)
