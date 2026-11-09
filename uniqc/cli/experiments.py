"""Experiments CLI: read-only coverage manifest for tomography/mitigation flows."""

from __future__ import annotations

import json

import typer

from uniqc.cli.output import console

HELP = "List experiment coverage: unified interfaces, local verification, frozen re-test commands, record sources."

app = typer.Typer(no_args_is_help=True, help=HELP)


@app.command("list")
def list_experiments(
    json_output: bool = typer.Option(False, "--json", help="Emit the manifest as JSON."),
    category: str = typer.Option(
        None, "--category", help="Filter by category (calibration/mitigation/tomography/benchmark)."
    ),
) -> None:
    """Show every audited experiment entry with its verification and re-test paths."""
    from uniqc.experiments import get_manifest

    manifest = get_manifest()
    if category:
        manifest = [entry for entry in manifest if entry["category"] == category]
    if json_output:
        console.print_json(json.dumps(manifest, ensure_ascii=False))
        return
    for entry in manifest:
        console.print(f"[bold cyan][{entry['id']}][/bold cyan] {entry['name']}  ({entry['category']})")
        console.print(f"  status          : {entry['status']}")
        for iface in entry["unified_interface"]:
            console.print(f"  interface       : {iface}")
        console.print(f"  local verify    : {entry['local_verify'] or '—'}")
        console.print(f"  re-test command : {entry['retest_command'] or '—'}")
        if entry["retest_note"]:
            console.print(f"  re-test note    : {entry['retest_note']}")
        console.print("")


@app.command("show")
def show(
    experiment_id: str = typer.Argument(..., help="Experiment id, e.g. 'readout_em'."),
    json_output: bool = typer.Option(False, "--json", help="Emit the entry as JSON."),
) -> None:
    """Show one experiment entry in full detail."""
    from uniqc.experiments import get_manifest

    manifest = get_manifest()
    entry = next((item for item in manifest if item["id"] == experiment_id), None)
    if entry is None:
        known = ", ".join(item["id"] for item in manifest)
        console.print(f"[red]Unknown experiment '{experiment_id}'. Known: {known}[/red]")
        raise typer.Exit(1)
    if json_output:
        console.print_json(json.dumps(entry, ensure_ascii=False))
        return
    console.print(f"[bold cyan][{entry['id']}][/bold cyan] {entry['name']}  ({entry['category']})")
    for key, value in entry.items():
        if key in ("id", "name", "category"):
            continue
        if isinstance(value, list):
            for item in value:
                console.print(f"  {key:<15}: {item}")
        else:
            console.print(f"  {key:<15}: {value}")
