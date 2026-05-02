"""``uniqc calibrate`` CLI subcommand.

Provides calibration experiment commands for XEB benchmarking and readout calibration.
"""

from __future__ import annotations

import json
import pathlib
import sys
from typing import Any

import typer

from uniqc.cli.output import (
    AI_HINTS_OPTION,
    console,
    print_error,
    print_info,
    print_success,
)

app = typer.Typer(help="Run chip calibration experiments (XEB, readout, patterns).")

HELP = "Run calibration experiments: XEB benchmarking and readout error calibration."


@app.command("xeb", help="Run cross-entropy benchmarking (1q and/or 2q).")
def xeb_cmd(
    qubits: list[int] | None = typer.Option(None, "--qubits", "-q", help="Qubit indices"),
    xeb_type: str = typer.Option("both", "--type", help="1q, 2q, or both"),
    shots: int = typer.Option(1000, "--shots", help="Shots per circuit"),
    depths: list[int] | None = typer.Option(None, "--depths", "-d", help="Circuit depths"),
    n_circuits: int = typer.Option(50, "--n-circuits", help="Circuits per depth"),
    pattern: str = typer.Option("auto", "--pattern", help="auto or circuit"),
    circuit_file: str | None = typer.Option(None, "--circuit", help="OriginIR file for circuit-based pattern"),
    backend: str = typer.Option("dummy", "--backend", "-b", help="Backend name"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output JSON file"),
    no_readout_em: bool = typer.Option(False, "--no-readout-em", help="Skip readout EM"),
    max_age_hours: float = typer.Option(24.0, "--max-age-hours", help="Max calibration data age"),
    seed: int | None = typer.Option(None, "--seed", help="Random seed"),
    ctx: typer.Context = typer.Context,
) -> None:
    """Run XEB benchmarking on specified qubits."""
    from uniqc.algorithm import xeb_workflow
    from uniqc.calibration.xeb.patterns import ParallelPatternGenerator

    if depths is None:
        depths = [5, 10, 20, 50]
    if qubits is None:
        qubits = [0, 1, 2, 3]

    print_info(f"XEB on backend={backend}, qubits={qubits}, type={xeb_type}")

    # Pattern analysis
    if pattern == "circuit":
        if circuit_file:
            path = pathlib.Path(circuit_file)
            if not path.exists():
                print_error(f"Circuit file not found: {circuit_file}")
                raise typer.Exit(1)
            originir = path.read_text()
            gen = ParallelPatternGenerator(topology=[])
            pat_result = gen.from_circuit(originir)
            print_info(f"Circuit pattern: {pat_result.n_rounds} rounds, "
                        f"{pat_result.chromatic_number} chromatic number")
            print_success(f"Groups: {pat_result.groups}")
        else:
            print_error("--circuit required for circuit-based pattern analysis")
            raise typer.Exit(1)
        return

    # Run XEB
    try:
        from uniqc.task.adapters import DummyAdapter, OriginQAdapter

        adapter_kwargs: dict[str, Any] = {}
        chip_char = None
        if backend == "dummy":
            adapter = DummyAdapter()
        elif backend.startswith("origin"):
            adapter = OriginQAdapter()
        else:
            adapter = DummyAdapter()

        # Determine pairs from chip topology
        edges: list[tuple[int, int]] = []
        if chip_char is not None:
            edges = [(e.u, e.v) for e in chip_char.connectivity]
            if qubits:
                target = set(qubits)
                edges = [(u, v) for u, v in edges if u in target and v in target]

        results: dict[str, Any] = {}

        if xeb_type in ("1q", "both"):
            print_info("Running 1q XEB...")
            results_1q = xeb_workflow.run_1q_xeb_workflow(
                backend=backend,
                qubits=qubits,
                depths=depths,
                n_circuits=n_circuits,
                shots=shots,
                use_readout_em=not no_readout_em,
                max_age_hours=max_age_hours,
                chip_characterization=chip_char,
                seed=seed,
            )
            results["1q"] = {str(k): v.to_dict() for k, v in results_1q.items()}
            for q, r in results_1q.items():
                console.print(f"  Qubit {q}: r={r.fidelity_per_layer:.5f} ± {r.fidelity_std_error:.5f}")

        if xeb_type in ("2q", "both"):
            if not edges:
                print_warning("No chip topology available for 2q XEB — skipping")
            else:
                print_info(f"Running 2q XEB on pairs: {edges}")
                results_2q = xeb_workflow.run_2q_xeb_workflow(
                    backend=backend,
                    pairs=edges,
                    depths=depths,
                    n_circuits=n_circuits,
                    shots=shots,
                    use_readout_em=not no_readout_em,
                    max_age_hours=max_age_hours,
                    chip_characterization=chip_char,
                    seed=seed,
                )
                results["2q"] = {str(k): v.to_dict() for k, v in results_2q.items()}
                for pair, r in results_2q.items():
                    console.print(f"  Pair {pair}: r={r.fidelity_per_layer:.5f} ± {r.fidelity_std_error:.5f}")

        print_success("XEB complete!")

        if output:
            with open(output, "w") as f:
                json.dump(results, f, indent=2)
            console.print(f"Results saved to [bold]{output}[/bold]")

    except Exception as e:
        print_error(f"XEB failed: {e}")
        raise typer.Exit(1)


@app.command("readout", help="Run readout error calibration (1q and/or 2q).")
def readout_cmd(
    qubits: list[int] | None = typer.Option(None, "--qubits", "-q", help="Qubit indices"),
    readout_type: str = typer.Option("both", "--type", help="1q, 2q, or both"),
    shots: int = typer.Option(1000, "--shots", help="Shots per calibration circuit"),
    backend: str = typer.Option("dummy", "--backend", "-b", help="Backend name"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output JSON file"),
    max_age_hours: float = typer.Option(24.0, "--max-age-hours", help="Max calibration data age"),
    ctx: typer.Context = typer.Context,
) -> None:
    """Run readout calibration and save confusion matrices."""
    from uniqc.calibration.readout import ReadoutCalibrator
    from uniqc.task.adapters import DummyAdapter, OriginQAdapter

    if qubits is None:
        qubits = [0, 1, 2, 3]

    print_info(f"Readout calibration on backend={backend}")

    if backend == "dummy":
        adapter = DummyAdapter()
    elif backend.startswith("origin"):
        adapter = OriginQAdapter()
    else:
        adapter = DummyAdapter()

    calibrator = ReadoutCalibrator(adapter=adapter, shots=shots)
    results: dict[str, Any] = {}

    if readout_type in ("1q", "both"):
        print_info("Calibrating 1q readout...")
        for q in qubits:
            r = calibrator.calibrate_1q(q)
            results[f"1q_q{q}"] = r
            console.print(f"  Qubit {q}: assignment fidelity = {r['assignment_fidelity']:.5f}")

    if readout_type in ("2q", "both"):
        from uniqc.task.adapters.dummy_adapter import DummyAdapter as DA
        if isinstance(adapter, DA):
            # Use connectivity from dummy adapter if available
            topology = adapter.available_topology or [(i, i + 1) for i in range(len(qubits) - 1)]
        else:
            topology = [(i, i + 1) for i in range(len(qubits) - 1)]
        pairs = [(topology[i][0], topology[i][1]) for i in range(len(topology))]
        if qubits:
            target = set(qubits)
            pairs = [(u, v) for u, v in pairs if u in target and v in target]

        print_info(f"Calibrating 2q readout for pairs: {pairs}")
        for pu, pv in pairs:
            r = calibrator.calibrate_2q(pu, pv)
            results[f"2q_{pu}_{pv}"] = r
            console.print(f"  Pair ({pu},{pv}): assignment fidelity = {r['assignment_fidelity']:.5f}")

    print_success("Readout calibration complete!")

    if output:
        with open(output, "w") as f:
            json.dump(results, f, indent=2)
        console.print(f"Results saved to [bold]{output}[/bold]")


@app.command("pattern", help="Analyze parallel execution patterns for 2-qubit gates.")
def pattern_cmd(
    qubits: list[int] | None = typer.Option(None, "--qubits", "-q", help="Qubit indices"),
    pattern_type: str = typer.Option("auto", "--type", help="auto or circuit"),
    circuit_file: str | None = typer.Option(None, "--circuit", "-c", help="OriginIR file for circuit mode"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output JSON file"),
    ctx: typer.Context = typer.Context,
) -> None:
    """Analyze parallel execution patterns for 2-qubit gates."""
    from uniqc.calibration.xeb.patterns import ParallelPatternGenerator

    if pattern_type == "circuit":
        if not circuit_file:
            print_error("--circuit required for circuit-based pattern analysis")
            raise typer.Exit(1)
        path = pathlib.Path(circuit_file)
        if not path.exists():
            print_error(f"Circuit file not found: {circuit_file}")
            raise typer.Exit(1)
        originir = path.read_text()
        # For circuit mode, we don't need topology
        gen = ParallelPatternGenerator(topology=[])
        result = gen.from_circuit(originir)
    else:
        # Auto mode: need topology
        if qubits is None:
            qubits = [0, 1, 2, 3]
        # Build simple chain topology if none provided
        topology = [(qubits[i], qubits[i + 1]) for i in range(len(qubits) - 1)]
        gen = ParallelPatternGenerator(topology=topology)
        result = gen.auto_generate()

    console.print(f"[bold]Parallel Pattern Analysis[/bold]")
    console.print(f"  Source: {result.source}")
    console.print(f"  Parallel rounds: {result.n_rounds}")
    console.print(f"  Chromatic number: {result.chromatic_number}")
    for i, group in enumerate(result.groups):
        console.print(f"  Round {i + 1}: {list(group)}")

    if output:
        with open(output, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        console.print(f"Results saved to [bold]{output}[/bold]")
