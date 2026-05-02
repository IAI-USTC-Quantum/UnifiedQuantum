"""Local simulation subcommand."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import typer

from .output import AI_HINTS_OPTION, build_ref_str, print_ai_hints
from .output import console, format_prob, print_error, print_json, print_table, write_output

HELP = (
    "Local circuit simulation\n"
    f"  {build_ref_str('simulate')}"
)


def simulate(
    input_file: Path = typer.Argument(..., help="Circuit file (OriginIR or QASM)", exists=True),
    backend: str = typer.Option("statevector", "--backend", "-b", help="Backend type: statevector/density"),
    shots: int = typer.Option(1024, "--shots", "-s", help="Number of measurement shots"),
    format: str = typer.Option("table", "--format", "-f", help="Output format: table/json"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file"),
    ai_hints: bool = AI_HINTS_OPTION,
):
    """Simulate a quantum circuit locally.

    Workflow:
      - Use --backend statevector for exact probabilities (default, fast).
      - Use --backend density for noisy simulation of NISQ devices.
      - Use --shots to set measurement repetitions (default 1024).
      - Use --format json for machine-readable output; --output to write to a file.
    """
    if ai_hints or os.environ.get("UNIQC_AI_HINTS"):
        print_ai_hints("simulate")

    content = input_file.read_text(encoding="utf-8")

    if backend not in ("statevector", "density"):
        print_error(f"Unknown backend: {backend}. Use 'statevector' or 'density'.")
        raise typer.Exit(1)

    try:
        result = _run_simulation(content, backend, shots)
    except Exception as e:
        print_error(str(e))
        raise typer.Exit(1)

    if format == "json":
        data = {"backend": backend, "shots": shots, "results": result}
        write_output(
            __import__("json").dumps(data, indent=2, ensure_ascii=False),
            str(output) if output else None,
        )
    else:
        _print_results_table(result, shots)
        if output:
            import json

            data = {"backend": backend, "shots": shots, "results": result}
            output.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            console.print(f"\n[dim]Results saved to {output}[/dim]")


def _run_simulation(content: str, backend: str, shots: int) -> dict[str, float]:
    """Run simulation and return measurement probabilities keyed by bitstring.

    Accepts both OriginIR and OpenQASM 2.0 input, dispatching to the matching
    simulator. Format detection reuses :func:`uniqc.cli.circuit._detect_format`;
    unknown content falls back to the OriginIR simulator so its existing error
    messages stay visible to the user.
    """
    from uniqc.cli.circuit import _detect_format
    from uniqc.originir import OriginIR_BaseParser
    from uniqc.qasm import OpenQASM2_BaseParser
    from uniqc.simulator import OriginIR_Simulator
    from uniqc.simulator.qasm_simulator import QASM_Simulator

    source_format = _detect_format(content)

    # Normalise CLI backend names to Python API names
    backend_type = "densitymatrix" if backend == "density" else backend

    if source_format == "qasm":
        parser = OpenQASM2_BaseParser()
        parser.parse(content)
        sim = QASM_Simulator(backend_type=backend_type)
    else:
        parser = OriginIR_BaseParser()
        parser.parse(content)
        sim = OriginIR_Simulator(backend_type=backend_type)

    n_qubits = max(int(parser.n_qubit or 1), 1)

    def _fmt(state: int) -> str:
        return format(int(state), f"0{n_qubits}b")

    if backend == "statevector":
        # simulate_pmeasure returns a 1-D array/list of length 2^n indexed
        # by computational basis state.
        probs = sim.simulate_pmeasure(content)
        return {
            _fmt(i): float(p)
            for i, p in enumerate(probs)
            if float(p) > 1e-10
        }

    # density matrix backend
    counts = sim.simulate_shots(content, shots=shots)
    total = sum(counts.values()) or 1
    return {_fmt(state): count / total for state, count in counts.items()}


def _print_results_table(results: dict[str, float], shots: int) -> None:
    """Print simulation results as a table."""
    sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)
    rows = []
    for state, prob in sorted_results:
        count = int(prob * shots)
        rows.append([state, str(count), format_prob(prob)])

    print_table(
        "Simulation Results",
        ["State", "Count", "Probability"],
        rows,
    )
