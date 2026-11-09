"""Benchmark CLI: reproducible QV and local compile/execute throughput entries."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from uniqc.cli.output import console

HELP = "Reproducible local benchmark entries (Quantum Volume, compile/execute throughput)."

app = typer.Typer(no_args_is_help=True, help=HELP)


def _write_report(report: dict, output: Path | None) -> None:
    if output is None:
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    console.print(f"[green]Report written to[/green] {output}")


@app.command("qv")
def qv(
    width: int = typer.Option(4, "--width", "-w", min=1, help="Model-circuit width m; QV=2**m on success."),
    trials: int = typer.Option(20, "--trials", "-n", min=1, help="Number of independent model circuits."),
    shots: int = typer.Option(1000, "--shots", min=1, help="Shots per circuit (acceptance configuration: 1000)."),
    seed: int = typer.Option(0, "--seed", help="Base seed; trial i uses seed+i."),
    output: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Write the full JSON report to this file.",
    ),
) -> None:
    """Run a seeded Quantum Volume benchmark on the local simulator.

    Implements the Cross et al. (2019) criterion: per trial h-2σ>2/3, run
    mean_h-2σ_mean>2/3; on success the backend is credited QV=2**width.
    Local evidence only — no cloud task is submitted.
    """
    from uniqc.benchmark import run_quantum_volume

    result = run_quantum_volume(width=width, trials=trials, shots=shots, base_seed=seed)
    verdict = "[green]PASSED[/green]" if result.passed else "[red]FAILED[/red]"
    console.print(f"Quantum Volume benchmark [bold]width={width}[/bold] trials={trials} shots={shots} seed={seed}")
    console.print(f"  mean heavy-output probability : {result.mean_h:.4f} ± {result.sigma_mean:.4f}")
    console.print(f"  trials passed                 : {result.trials_passed}/{result.trials}")
    console.print(f"  criterion mean_h - 2σ > 2/3   : {verdict}")
    if result.passed:
        console.print(f"  [bold cyan]Quantum Volume = {result.quantum_volume}[/bold cyan]")
    else:
        console.print("  Quantum Volume not achieved at this width.")
    _write_report(result.to_json_dict(), output)
    if not result.passed:
        raise typer.Exit(1)


@app.command("throughput")
def throughput(
    circuits: int = typer.Option(500, "--circuits", "-n", min=1, help="Number of circuits in the input set."),
    qubits: int = typer.Option(8, "--qubits", "-q", min=1, help="Qubits per circuit."),
    depth: int = typer.Option(6, "--depth", "-d", min=1, help="Entangling layers per circuit."),
    shots: int = typer.Option(1000, "--shots", min=1, help="Shots per circuit (acceptance configuration: 1000)."),
    seed: int = typer.Option(0, "--seed", help="Base seed; circuit i uses seed+i."),
    backend: str = typer.Option("dummy:local:simulator", "--backend", "-b", help="Local backend fixture identifier."),
    output: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Write the full JSON report to this file.",
    ),
) -> None:
    """Measure local compile/execute throughput (circuits/hour).

    Timed boundary per circuit: OriginIR parse/preprocess (compile) +
    statevector simulation + shot sampling (execute). Process startup, task
    persistence and report I/O are excluded. Exit code 1 if the measured
    rate is below 30,000 circuits/hour.
    """
    from uniqc.benchmark import run_throughput_benchmark

    result = run_throughput_benchmark(
        circuits=circuits,
        n_qubits=qubits,
        depth=depth,
        shots=shots,
        seed=seed,
        backend_id=backend,
    )
    verdict = "[green]PASS[/green]" if result.meets_30000_per_hour else "[red]BELOW 30,000/h[/red]"
    console.print(
        f"Local compile/execute throughput [bold]{circuits}[/bold] circuits × "
        f"{qubits}q depth {depth}, {shots} shots/circuit, seed={seed}, backend={result.backend_id}"
    )
    console.print(f"  compile   : {result.compile_seconds:.3f}s  ({result.compile_circuits_per_hour:,.0f} circuits/h)")
    console.print(f"  execute   : {result.execute_seconds:.3f}s  ({result.execute_circuits_per_hour:,.0f} circuits/h)")
    console.print(
        f"  total     : {result.total_seconds:.3f}s  -> [bold cyan]{result.circuits_per_hour:,.0f} circuits/h[/bold cyan]"
    )
    console.print(f"  >= 30,000 circuits/hour : {verdict}")
    _write_report(result.to_json_dict(), output)
    if not result.meets_30000_per_hour:
        raise typer.Exit(1)
