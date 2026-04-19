"""Local simulation subcommand."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from .output import console, format_prob, print_error, print_json, print_table, write_output

app = typer.Typer(help="Local circuit simulation")


@app.callback(invoke_without_command=True)
def simulate(
    input_file: Path = typer.Argument(..., help="Circuit file (OriginIR or QASM)", exists=True),
    backend: str = typer.Option("statevector", "--backend", "-b", help="Backend type: statevector/density"),
    shots: int = typer.Option(1024, "--shots", "-s", help="Number of measurement shots"),
    format: str = typer.Option("table", "--format", "-f", help="Output format: table/json"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file"),
):
    """Simulate a quantum circuit locally."""
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
    """Run simulation and return measurement results keyed by bitstring."""
    from uniqc.originir import OriginIR_BaseParser
    from uniqc.simulator import OriginIR_Simulator

    parser = OriginIR_BaseParser()
    parser.parse(content)
    n_qubits = max(int(parser.n_qubit), 1)

    def _fmt(state: int) -> str:
        return format(int(state), f"0{n_qubits}b")

    sim = OriginIR_Simulator(backend_type=backend)
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
