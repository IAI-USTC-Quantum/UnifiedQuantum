"""Cloud task submission subcommand."""

from __future__ import annotations

import os
from pathlib import Path

import typer

from uniqc.backend_adapter.task.result_types import DryRunResult

from .output import AI_HINTS_OPTION, build_ref_str, print_ai_hints, print_error, print_json, print_success, print_table

HELP = f"Submit circuits to quantum cloud platforms\n  {build_ref_str('submit')}"
INPUT_FILES_ARGUMENT = typer.Argument(..., help="Circuit file(s) to submit", exists=True)
PLATFORM_OPTION = typer.Option(..., "--platform", "-p", help="Platform: originq/quafu/ibm/dummy")
BACKEND_OPTION = typer.Option(None, "--backend", "-b", help="Backend name (e.g., 'origin:wuyuan:d5' for OriginQ)")
SHOTS_OPTION = typer.Option(1000, "--shots", "-s", help="Number of measurement shots")
NAME_OPTION = typer.Option(None, "--name", help="Task name")
WAIT_OPTION = typer.Option(False, "--wait", "-w", help="Wait for result after submission")
TIMEOUT_OPTION = typer.Option(300.0, "--timeout", help="Timeout in seconds when waiting")
FORMAT_OPTION = typer.Option("table", "--format", "-f", help="Output format: table/json")
DRY_RUN_OPTION = typer.Option(
    False,
    "--dry-run",
    help="Validate the circuit(s) without submitting. Checks translation, "
    "gate compatibility, and qubit count limits — makes no network calls.",
)


def _handle_dry_run(
    circuits: list[str],
    platform: str,
    backend_name: str | None,
    shots: int,
    format: str,
) -> None:
    """Run dry-run validation on circuits and print results."""
    from uniqc.backend_adapter.task_manager import dry_run_task

    parsed = [_parse_to_circuit(c) for c in circuits]

    # Build kwargs for backend-specific options
    # --backend maps to backend_name for OriginQ, chip_id for IBM/Quafu
    kwargs: dict = {}
    if backend_name:
        if platform == "originq":
            kwargs["backend_name"] = backend_name
        elif platform in ("ibm", "quafu"):
            kwargs["chip_id"] = backend_name

    # Use 'originq' as the backend key for dummy platform
    backend_key = "originq" if platform == "dummy" else platform

    results: list[DryRunResult] = []
    for circuit in parsed:
        result = dry_run_task(
            circuit,
            backend=backend_key,
            shots=shots,
            dummy=(platform == "dummy"),
            **kwargs,
        )
        results.append(result)

    # Print results
    if format == "json":
        print_json(
            {
                "dry_run": True,
                "platform": platform,
                "results": [
                    {
                        "success": r.success,
                        "details": r.details,
                        "error": r.error,
                        "warnings": list(r.warnings),
                        "backend_name": r.backend_name,
                        "circuit_qubits": r.circuit_qubits,
                        "supported_gates": list(r.supported_gates),
                    }
                    for r in results
                ],
            }
        )
    else:
        if len(results) == 1:
            _print_dry_run_result(results[0], platform)
        else:
            _print_dry_run_results(results, platform)


def _print_dry_run_result(result: DryRunResult, platform: str) -> None:
    """Print a single dry-run result in human-readable format."""
    from .output import print_error, print_success, print_warning

    if result.success:
        print_success(f"[DRY-RUN PASSED] {result.details}")
    else:
        print_error(f"[DRY-RUN FAILED] {result.error or 'Unknown error'}")
        print(f"  Details: {result.details}")

    if result.warnings:
        for w in result.warnings:
            print_warning(f"  Warning: {w}")

    if result.circuit_qubits is not None:
        print(f"  Circuit qubits: {result.circuit_qubits}")
    if result.backend_name:
        print(f"  Backend: {result.backend_name}")


def _print_dry_run_results(results: list[DryRunResult], platform: str) -> None:
    """Print multiple dry-run results as a table."""
    rows = []
    for i, r in enumerate(results):
        status = "PASS" if r.success else "FAIL"
        rows.append(
            [
                str(i + 1),
                status,
                r.backend_name or "-",
                str(r.circuit_qubits or "-"),
                r.error or r.details,
            ]
        )

    headers = ["#", "Status", "Backend", "Qubits", "Details/Error"]
    print_table("Dry-Run Results", headers, rows)


def submit(
    input_files: list[Path] = INPUT_FILES_ARGUMENT,
    platform: str = PLATFORM_OPTION,
    backend: str | None = BACKEND_OPTION,
    shots: int = SHOTS_OPTION,
    name: str | None = NAME_OPTION,
    wait: bool = WAIT_OPTION,
    timeout: float = TIMEOUT_OPTION,
    format: str = FORMAT_OPTION,
    ai_hints: bool = AI_HINTS_OPTION,
    dry_run: bool = DRY_RUN_OPTION,
):
    """Submit circuit(s) to a quantum cloud platform.

    Workflow:
      - After submission you receive a TASK_ID.
      - Check result: uniqc result <TASK_ID>
      - List all tasks: uniqc task list
      - Validate config first: uniqc config validate
      - Pick a backend: uniqc backend list --platform <PLATFORM>
    """
    if ai_hints or os.environ.get("UNIQC_AI_HINTS"):
        print_ai_hints("submit")

    if platform not in ("originq", "quafu", "ibm", "dummy"):
        print_error(f"Unknown platform: {platform}. Use originq/quafu/ibm/dummy.")
        raise typer.Exit(1)

    circuits = []
    for path in input_files:
        circuits.append(path.read_text(encoding="utf-8"))

    # Dry-run: validate without submitting
    if dry_run:
        _handle_dry_run(circuits, platform, backend, shots, format)
        raise typer.Exit(0)

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
    from uniqc.compile.originir import OriginIR_BaseParser

    parser = OriginIR_BaseParser()
    try:
        parser.parse(circuit_text)
        return parser.to_circuit()
    except Exception:
        # Fall back to QASM
        from uniqc.compile.qasm import OpenQASM2_BaseParser

        qasm_parser = OpenQASM2_BaseParser()
        qasm_parser.parse(circuit_text)
        return qasm_parser.to_circuit()


def _submit_single(circuit: str, platform: str, backend_name: str | None, shots: int, name: str | None) -> str:
    """Submit a single circuit using the unified task_manager API."""
    from uniqc.backend_adapter.task_manager import submit_task

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


def _submit_batch(
    circuits: list[str], platform: str, backend_name: str | None, shots: int, name: str | None
) -> list[str]:
    """Submit multiple circuits using the unified task_manager API."""
    from uniqc.backend_adapter.task_manager import submit_batch

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
    backend = "dummy" if dummy else platform

    return submit_batch(parsed_circuits, backend=backend, dummy=dummy, **kwargs)


def _wait_and_show(task_id: str, platform: str, timeout: float, format: str) -> None:
    """Wait for task result and display it."""
    from .result import show_result

    show_result(task_id, platform=platform, wait=True, timeout=timeout, format=format)
