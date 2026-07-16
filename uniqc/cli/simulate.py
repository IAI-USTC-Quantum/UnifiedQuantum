"""Local simulation subcommand."""

from __future__ import annotations

from pathlib import Path

import typer

from .output import (
    AI_HINTS_OPTION,
    ai_hints_enabled,
    build_ref_str,
    console,
    format_prob,
    print_ai_hints,
    print_error,
    print_table,
    write_output,
)

HELP = f"Local circuit simulation\n  {build_ref_str('simulate')}"


def simulate(
    input_file: Path = typer.Argument(..., help="Circuit file (OriginIR or QASM)", exists=True),
    backend: str = typer.Option(
        "statevector",
        "--backend",
        "-b",
        help=("Backend type: statevector / density (alias: density_matrix, densitymatrix)"),
    ),
    shots: int = typer.Option(1024, "--shots", "-s", help="Number of measurement shots"),
    format: str = typer.Option("table", "--format", "-f", help="Output format: table/json"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output file"),
    ai_hints: bool = AI_HINTS_OPTION,
):
    """Simulate a quantum circuit locally.

    Workflow:
      - Use --backend statevector for exact probabilities (default, fast).
      - Use --backend density (or alias: density_matrix / densitymatrix) for
        noisy simulation of NISQ devices.
      - Use --shots to set measurement repetitions (default 1024).
      - Use --format json for machine-readable output; --output to write to a file.
    """
    if ai_hints_enabled(ai_hints):
        print_ai_hints("simulate")

    content = input_file.read_text(encoding="utf-8")

    _DENSITY_ALIASES = {"density", "density_matrix", "densitymatrix"}
    if backend == "statevector":
        backend_canonical = "statevector"
    elif backend in _DENSITY_ALIASES:
        backend_canonical = "density"
    else:
        print_error(
            f"Unknown backend: {backend}. Use 'statevector' or 'density' (alias: density_matrix, densitymatrix)."
        )
        raise typer.Exit(1)
    backend = backend_canonical

    try:
        result = _run_simulation(content, backend, shots)
    except Exception as e:
        print_error(str(e))
        raise typer.Exit(1) from e

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
    from uniqc.simulator import Simulator

    # Normalise CLI backend names to Python API names
    backend_type = "densitymatrix" if backend == "density" else backend

    # Dynamic OriginIR-ext programs (mid-circuit MEASURE + classical control
    # flow) are stochastic: route them to the CREG-aware simulator and report
    # per-shot sampled probabilities keyed by the CREG bitstring.
    from uniqc.circuit_builder.classical_program import contains_dynamic_keywords

    if contains_dynamic_keywords(content):
        from uniqc.simulator import OriginIR_ext_Simulator

        dyn_sim = OriginIR_ext_Simulator(backend_type=backend_type)
        counts = dyn_sim.simulate_shots(content, shots=shots)
        n_bits = max(int(dyn_sim.n_cbit or 1), 1)
        total = sum(counts.values()) or 1
        return {format(int(state), f"0{n_bits}b"): count / total for state, count in counts.items()}

    sim = Simulator(backend_type=backend_type)
    sim.simulate_preprocess(content)

    n_qubits = max(int(sim.qubit_num or 1), 1)

    def _fmt(state: int) -> str:
        return format(int(state), f"0{n_qubits}b")

    if backend == "statevector":
        # simulate_pmeasure returns a 1-D array/list of length 2^n indexed
        # by computational basis state.
        probs = sim.simulate_pmeasure(content)
        return {_fmt(i): float(p) for i, p in enumerate(probs) if float(p) > 1e-10}

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
