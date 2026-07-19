"""``uniqc backend virtual`` CLI subcommands.

Manage user-defined noisy virtual machines stored as YAML files under
``~/.uniqc/backend/virtual/``. A configured machine is used as
``dummy:virtual:<name>`` anywhere a backend identifier is accepted.
"""

from __future__ import annotations

import rich.box
import typer

from uniqc.backend_adapter import virtual_machine as _vm
from uniqc.backend_adapter.virtual_machine import (
    VirtualMachineConfig,
    create_virtual_machine_template,
    load_virtual_machine,
    scan_virtual_machines,
)
from uniqc.cli.output import console, print_error, print_success, print_warning

app = typer.Typer(
    help="Manage user-defined noisy virtual machines (~/.uniqc/backend/virtual/*.yaml)",
)


def _noise_summary(config: VirtualMachineConfig) -> str:
    parts: list[str] = []
    if config.depol_1q or config.depol_2q:
        parts.append("depol")
    if config.gate_type_depol:
        parts.append(f"gate-type({len(config.gate_type_depol)})")
    if config.gate_instance_depol:
        parts.append(f"instance({len(config.gate_instance_depol)})")
    if config.t1_us or config.t2_us:
        parts.append("T1/T2")
    if config.readout:
        parts.append("readout")
    return ", ".join(parts) if parts else "none (noiseless)"


@app.command("init")
def init(
    name: str = typer.Argument(..., help="Virtual machine name (letters, digits, '-' and '_')"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite an existing config file"),
):
    """Create a commented template config at ~/.uniqc/backend/virtual/<name>.yaml.

    Workflow:
      - Edit the generated YAML (topology, gate errors, readout, T1/T2).
      - Validate it: uniqc backend virtual validate <name>
      - Use it: uniqc submit circuit.qasm --backend dummy:virtual:<name>
    """
    try:
        path = create_virtual_machine_template(name, force=force)
    except FileExistsError:
        print_error(f"Config for '{name}' already exists (use --force to overwrite).")
        raise typer.Exit(1) from None
    except ValueError as exc:
        print_error(str(exc))
        raise typer.Exit(1) from None
    print_success(f"Created {path}")
    console.print(f"  Next: edit it, then run [bold]uniqc backend virtual validate {name}[/bold]")
    console.print(f"  Use: [bold]uniqc submit circuit.qasm --backend dummy:virtual:{name}[/bold]")


@app.command("list")
def list_machines():
    """List all virtual machines under ~/.uniqc/backend/virtual/."""
    entries = scan_virtual_machines()
    if not entries:
        print_warning(f"No virtual machines found in {_vm.DEFAULT_VIRTUAL_DIR}.")
        console.print("  Create one with: [bold]uniqc backend virtual init <name>[/bold]")
        raise typer.Exit(0)

    from rich.table import Table

    table = Table(
        title=f"Virtual Machines ({_vm.DEFAULT_VIRTUAL_DIR})",
        box=rich.box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Name", style="bold white", min_width=12)
    table.add_column("Qubits", justify="right", width=8)
    table.add_column("Edges", justify="right", width=8)
    table.add_column("Noise")
    table.add_column("Status", width=10)
    for entry in entries:
        if entry.config is None:
            table.add_row(entry.name, "-", "-", "-", "[red]invalid[/red]")
            continue
        config = entry.config
        table.add_row(
            config.name,
            str(len(config.qubits)),
            str(len(config.topology)),
            _noise_summary(config),
            "[green]ok[/green]",
        )
    console.print(table)

    for entry in entries:
        if entry.config is None:
            print_warning(f"{entry.path.name}: {entry.error}")


@app.command("show")
def show(
    name: str = typer.Argument(..., help="Virtual machine name"),
):
    """Show the parsed config and derived noise parameters of a virtual machine."""
    try:
        config = load_virtual_machine(name)
    except ValueError as exc:
        print_error(str(exc))
        raise typer.Exit(1) from None

    from rich.panel import Panel
    from rich.rule import Rule
    from rich.table import Table

    console.print(Rule(f"[bold cyan]virtual:{config.name}[/bold cyan]"))

    overview = [
        f"[bold]File:[/bold]        {config.source_path}",
        f"[bold]Description:[/bold] {config.description or '-'}",
        f"[bold]Qubits:[/bold]      {len(config.qubits)} ({', '.join(str(q) for q in config.qubits[:12])}{', ...' if len(config.qubits) > 12 else ''})",
        f"[bold]Topology:[/bold]    {len(config.topology)} edges"
        if config.topology
        else "[bold]Topology:[/bold]    unconstrained (all-to-all)",
        f"[bold]Reference:[/bold]   dummy:virtual:{config.name}",
    ]
    console.print(Panel("\n".join(overview), title="Overview", box=rich.box.ROUNDED))

    noise_lines: list[str] = []
    if config.depol_1q or config.depol_2q:
        noise_lines.append(f"[bold]Uniform depolarizing:[/bold] 1q={config.depol_1q or 0}, 2q={config.depol_2q or 0}")
    for gate, prob in sorted(config.gate_type_depol.items()):
        noise_lines.append(f"[bold]Gate type {gate}:[/bold] depolarizing {prob}")
    for (gate, qubits), prob in sorted(config.gate_instance_depol.items()):
        noise_lines.append(f"[bold]Instance {gate}{list(qubits)}:[/bold] depolarizing {prob}")
    if noise_lines:
        console.print(Panel("\n".join(noise_lines), title="Gate Error Model", box=rich.box.ROUNDED))

    if config.gate_times_ns:
        times = ", ".join(f"{k}={v}ns" for k, v in sorted(config.gate_times_ns.items()))
        console.print(f"[bold]Gate times:[/bold] {times}")

    thermal_qubits = sorted(set(config.t1_us) | set(config.t2_us))
    if thermal_qubits or config.readout:
        q_table = Table(title="Per-Qubit Noise", box=rich.box.ROUNDED, header_style="bold cyan")
        q_table.add_column("Qubit", justify="right", width=8)
        q_table.add_column("T1 (us)", justify="right", width=10)
        q_table.add_column("T2 (us)", justify="right", width=10)
        q_table.add_column("Readout p01", justify="right", width=12)
        q_table.add_column("Readout p10", justify="right", width=12)
        for q in sorted(set(thermal_qubits) | set(config.readout)):
            p01, p10 = config.readout.get(q, (None, None))
            q_table.add_row(
                str(q),
                f"{config.t1_us[q]:.1f}" if q in config.t1_us else "-",
                f"{config.t2_us[q]:.1f}" if q in config.t2_us else "-",
                f"{p01:.4f}" if p01 is not None else "-",
                f"{p10:.4f}" if p10 is not None else "-",
            )
        console.print(q_table)


@app.command("validate")
def validate(
    name: str = typer.Argument(..., help="Virtual machine name"),
):
    """Validate a virtual machine config file and print a summary."""
    try:
        config = load_virtual_machine(name)
    except ValueError as exc:
        print_error(str(exc))
        raise typer.Exit(1) from None
    print_success(f"{config.source_path}: valid")
    console.print(f"  Qubits: {len(config.qubits)}, topology edges: {len(config.topology)}")
    console.print(f"  Noise: {_noise_summary(config)}")
    console.print(f"  Use: [bold]uniqc submit circuit.qasm --backend dummy:virtual:{config.name}[/bold]")
