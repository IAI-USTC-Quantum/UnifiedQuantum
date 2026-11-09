"""Noise-bridge CLI: import exchange models and run QRAM/QPU/mitigation cases locally."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from uniqc.cli.output import console

HELP = "Import versioned noise-model exchange files and run local noisy-VM cases (no cloud tasks)."

app = typer.Typer(no_args_is_help=True, help=HELP)


@app.command("import")
def import_model(
    path: Path = typer.Argument(..., exists=True, readable=True, help="nlearn.noise-model.v1 exchange file."),
    output: Path = typer.Option(None, "--output", "-o", help="Write a validation summary JSON here."),
) -> None:
    """Validate an exchange model file and show its binding summary."""
    from uniqc.noise_bridge import load_noise_model

    model = load_noise_model(path)
    summary = {
        "schema": model.payload["schema"],
        "model_sha256": model.model_sha256,
        "data_class": model.data_class,
        "generator": model.generator,
        "physical_chain": model.physical_chain,
        "local_edges": [list(edge) for edge in model.local_edges],
        "readout_error": {str(q): rates for q, rates in sorted(model.readout_error().items())},
        "gate_channels": len(model.payload["consumer_bindings"]["uniqc.noisy_simulator.v1"]["gate_specific_errors"]),
        "edge_flip_entries": len(model.edge_flip_entries()),
        "path": str(path),
    }
    console.print(f"[green]Valid[/green] {summary['schema']} model (sha256 {summary['model_sha256'][:12]}…)")
    console.print(f"  data class     : {summary['data_class']}")
    console.print(f"  generator      : {summary['generator'].get('name')} {summary['generator'].get('version')}")
    console.print(f"  chain          : {summary['physical_chain']}")
    console.print(f"  gate channels  : {summary['gate_channels']}")
    console.print(f"  edge flips     : {summary['edge_flip_entries']}")
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        console.print(f"[green]Summary written to[/green] {output}")


@app.command("qram")
def qram_case(
    model_path: Path = typer.Argument(..., exists=True, readable=True, help="Exchange model file."),
    case: str = typer.Option(
        "lookup", "--case", help="Case: 'lookup' (basis address) or 'qpu' (superposition addressing)."
    ),
    address: int = typer.Option(5, "--address", min=0, max=7, help="Lookup address (lookup case only)."),
    shots: int = typer.Option(1000, "--shots", min=1, help="Shots."),
    seed: int = typer.Option(0, "--seed", help="Seed for shot sampling and edge flips."),
    output: Path = typer.Option(None, "--output", "-o", help="Write the full case report JSON here."),
    workdir: Path = typer.Option(
        None,
        "--workdir",
        help="Directory for the readout-EM calibration cache (default: a temp dir).",
    ),
) -> None:
    """Run a 3-layer QRAM case on the imported noisy VM with readout mitigation.

    The case runs entirely on the local density-operator simulator; no cloud
    task is submitted and no shots quota is consumed.
    """
    from uniqc.noise_bridge import load_noise_model, run_qpu_addressing_case, run_qram_lookup_case

    model = load_noise_model(model_path)
    if case == "lookup":
        report = run_qram_lookup_case(model, address=address, shots=shots, seed=seed, workdir=workdir)
        console.print(f"[bold]QRAM 3-layer lookup[/bold] address={address} shots={shots} seed={seed}")
        console.print(f"  expected value : {report['expected_value']} ({format(report['expected_value'], '02b')})")
        console.print(f"  raw accuracy   : {report['raw_accuracy']:.3f}  (top outcome {report['raw_top_outcome']})")
        console.print(
            f"  mitigated      : {report['mitigated_accuracy']:.3f}  (top outcome {report['mitigated_top_outcome']})"
        )
    elif case == "qpu":
        report = run_qpu_addressing_case(model, shots=shots, seed=seed, workdir=workdir)
        console.print(f"[bold]QPU addressing on 3-layer QRAM[/bold] shots={shots} seed={seed}")
        console.print(f"  ideal data distribution : {report['ideal_distribution']}")
        console.print(f"  raw fidelity            : {report['raw_fidelity']:.4f}")
        console.print(f"  mitigated fidelity      : {report['mitigated_fidelity']:.4f}")
    else:
        console.print(f"[red]Unknown case '{case}'. Use 'lookup' or 'qpu'.[/red]")
        raise typer.Exit(1)
    console.print(f"  model sha256   : {model.model_sha256[:12]}… ({model.data_class})")
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        console.print(f"[green]Report written to[/green] {output}")
