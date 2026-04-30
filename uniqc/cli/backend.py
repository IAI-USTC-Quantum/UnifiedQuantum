"""``uniqc backend`` CLI subcommand."""

from __future__ import annotations

import os
import sys

import rich.box
import typer

from uniqc.backend_cache import cache_info, invalidate_all
from uniqc.backend_info import BackendInfo, Platform
from uniqc.backend_registry import fetch_all_backends, fetch_platform_backends, find_backend
from uniqc.cli.output import (
    AI_HINTS_OPTION,
    build_ref_str,
    console,
    print_ai_hints,
    print_error,
    print_info,
    print_success,
    print_warning,
)

app = typer.Typer(
    help=(
        "List, update, and inspect quantum cloud backends\n"
        f"  {build_ref_str('backend-list')}"
    ),
)


# Detect whether a subcommand was given by checking if the first
# positional arg in sys.argv matches a known subcommand name.
_SUB_COMMANDS = frozenset({"list", "update", "show", "chip-display"})


def _subcommand_given() -> bool:
    args = sys.argv
    # e.g. ['uniqc', 'backend', 'list', ...] → index 2 is the subcommand
    if len(args) >= 3 and args[1] == "backend":
        return args[2] in _SUB_COMMANDS
    return False


@app.callback(invoke_without_command=True)
def backend(
    ctx: typer.Context,
    show: str | None = typer.Option(
        None,
        "--show",
        "-s",
        help="Show detailed info for a specific backend (e.g. originq:full_amplitude)",
    ),
):
    """List, update, and inspect quantum cloud backends."""
    if _subcommand_given():
        return  # Let the subcommand handle it

    if show:
        try:
            b = find_backend(show)
            _print_backend_detail(b)
        except ValueError as exc:
            print_error(str(exc))
            raise typer.Exit(1)  # noqa: B904
        except Exception as exc:
            print_error(f"Failed to fetch backend: {exc}")
            raise typer.Exit(1)  # noqa: B904
        raise typer.Exit(0)

    # No args → default to list
    list_backends(
        platform=None,
        status_filter=None,
        format="table",
    )


def _fmt_fidelity(val: float | None) -> str:
    """Format a fidelity value as a 5-char string or '-' if unavailable."""
    if val is None:
        return "-"
    return f"{val:.4f}"


@app.command("list")
def list_backends(
    platform: str | None = typer.Option(
        None,
        "--platform",
        "-p",
        help="Only show backends for this platform (originq/quafu/ibm)",
    ),
    status_filter: str | None = typer.Option(
        None,
        "--status",
        "-s",
        help="Filter by status: available, unavailable, deprecated, simulator, hardware",
    ),
    all: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Show all backends including unavailable and deprecated (default: only available backends are shown)",
    ),
    info: bool = typer.Option(
        False,
        "--info",
        "-i",
        help="Show additional backend information (fidelity, coherence times)",
    ),
    format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: table (default) or json",
    ),
    ai_hints: bool = AI_HINTS_OPTION,
):
    """List backends from configured platforms.

    By default only available backends are shown. Use --all to show all backends
    regardless of status.

    Workflow:
      - No backends shown? Run uniqc backend update to fetch the latest backend list.
      - Select a backend: copy the Name column value and pass it to --backend in uniqc submit.
      - Hardware vs simulator: 'hw' = real device, 'sim' = simulation backend.
      - Use --status simulator or --status hardware to filter.
    """
    if ai_hints or os.environ.get("UNIQC_AI_HINTS"):
        print_ai_hints("backend-list")

    target_platform: Platform | None = None
    if platform:
        try:
            target_platform = Platform(platform.lower())
        except ValueError:
            print_error(f"Unknown platform '{platform}'. Valid: {', '.join(p.value for p in Platform)}")
            raise typer.Exit(1)  # noqa: B904

    if target_platform:
        try:
            backends, fresh = fetch_platform_backends(target_platform)
        except Exception as exc:
            print_error(f"Failed to fetch backends: {exc}")
            raise typer.Exit(1)  # noqa: B904
        all_backends: dict[Platform, list[BackendInfo]] = {}
        if backends:
            all_backends[target_platform] = backends
    else:
        try:
            all_backends = fetch_all_backends()
        except Exception as exc:
            print_error(f"Failed to fetch backends: {exc}")
            raise typer.Exit(1)  # noqa: B904

    if not all_backends:
        print_warning("No backends found. Run 'uniqc backend update' to fetch from APIs.")
        raise typer.Exit(0)

    # Apply status filter: explicit --status takes precedence; otherwise show
    # only available backends unless --all is given.
    def matches_filter(b: BackendInfo) -> bool:
        if status_filter == "simulator":
            return b.is_simulator
        if status_filter == "hardware":
            return b.is_hardware
        if status_filter == "available":
            return b.status == "available"
        if status_filter == "unavailable":
            return b.status == "unavailable"
        if status_filter == "deprecated":
            return b.status == "deprecated"
        if status_filter:
            return b.status.lower() == status_filter.lower()
        # Default: show only available backends unless --all is used
        return all or b.status == "available"

    # Build output rows
    rows: list[list[str]] = []
    json_data: list[dict] = []
    for plat, backends in all_backends.items():
        for b in backends:
            if not matches_filter(b):
                continue
            if info:
                rows.append(
                    [
                        plat.value,
                        b.name,
                        str(b.num_qubits) if b.num_qubits else "-",
                        b.status,
                        "sim" if b.is_simulator else "hw",
                        _fmt_fidelity(b.avg_1q_fidelity),
                        _fmt_fidelity(b.avg_2q_fidelity),
                    ]
                )
            else:
                rows.append(
                    [
                        plat.value,
                        b.name,
                        str(b.num_qubits) if b.num_qubits else "-",
                        b.status,
                        "sim" if b.is_simulator else "hw",
                    ]
                )
            json_data.append(b.to_dict())

    if format == "json":
        console.print_json(json_data)
        return

    if not rows:
        if status_filter:
            print_warning(f"No backends match filter '--status {status_filter}'")
        else:
            print_warning("No backends match the current filter.")
        return

    from rich.table import Table

    table = Table(
        title="Available Backends",
        box=rich.box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Platform", style="cyan", width=10)
    table.add_column("Name", style="bold white", min_width=20)
    table.add_column("Qubits", justify="right", width=8)
    table.add_column("Status", width=12)
    table.add_column("Type", width=6)
    if info:
        table.add_column("1Q Fid.", justify="right", width=9)
        table.add_column("2Q Fid.", justify="right", width=9)

    for row in rows:
        status_style = {
            "available": "green",
            "unavailable": "red",
            "deprecated": "yellow",
            "maintenance": "magenta",
        }.get(row[3], "")
        table.add_row(*row, style=status_style)
    console.print(table)

    # Show cache status
    info_cache = cache_info()
    if info_cache:
        lines = []
        for p, meta in info_cache.items():
            age = meta["age_seconds"]
            stale_marker = " [yellow](stale)[/yellow]" if meta["is_stale"] else ""
            age_str = _format_age(age)
            lines.append(f"  {p}: {meta['num_backends']} backends, updated {age_str} ago{stale_marker}")
        console.print("\n[dim]Cache:[/dim]")
        for line in lines:
            console.print(f"  {line}")


@app.command("update")
def update(
    platform: str | None = typer.Option(
        None,
        "--platform",
        "-p",
        help="Only update backends for this platform (originq/quafu/ibm)",
    ),
    clear: bool = typer.Option(
        False,
        "--clear",
        "-c",
        help="Clear cache before updating (force re-fetch all platforms)",
    ),
    ai_hints: bool = AI_HINTS_OPTION,
):
    """Force-refresh backend information from cloud APIs.

    Always bypasses the cache and fetches fresh data from all configured
    platforms. Use ``uniqc backend list`` to view cached data without refreshing.
    """
    if ai_hints or os.environ.get("UNIQC_AI_HINTS"):
        print_ai_hints("backend-list")

    if clear:
        invalidate_all()
        print_info("Cache cleared.")

    targets = [Platform(platform.lower())] if platform else list(Platform)
    updated_platforms: list[str] = []
    warnings_list: list[str] = []

    for plat in targets:
        try:
            backends, _ = fetch_platform_backends(plat, force_refresh=True)
            if backends:
                updated_platforms.append(f"{plat.value} ({len(backends)} backends)")
            else:
                warnings_list.append(f"{plat.value}: no backends returned")
        except Exception as exc:
            # Warn but don't fail — a single platform being down shouldn't abort
            # the whole update (especially IBM which may be network-restricted).
            warnings_list.append(f"{plat.value}: {exc}")

    if updated_platforms:
        print_success(f"Updated: {', '.join(updated_platforms)}")
    if warnings_list:
        for w in warnings_list:
            print_warning(f"Skipped: {w}")
    if not updated_platforms and not warnings_list:
        print_error("No backends updated.")
        raise typer.Exit(1)


@app.command("show")
def show(
    identifier: str = typer.Argument(..., help="Backend identifier (platform:name or bare name)"),
    format: str = typer.Option("rich", "--format", "-f", help="Output format: rich (default) or json"),
    ai_hints: bool = AI_HINTS_OPTION,
):
    """Show detailed information for a specific backend.

    Workflow:
      - Use this backend for submission: uniqc submit ... --backend '<IDENTIFIER>'
      - Compare backends: uniqc backend list --info to see fidelity data for all backends.
      - Hardware backends show fidelity data; lower fidelity = higher error rates on real devices.
    """
    if ai_hints or os.environ.get("UNIQC_AI_HINTS"):
        print_ai_hints("backend-show")

    try:
        backend = find_backend(identifier)
    except ValueError as exc:
        print_error(str(exc))
        raise typer.Exit(1)  # noqa: B904
    except Exception as exc:
        print_error(f"Failed to fetch backend: {exc}")
        raise typer.Exit(1)  # noqa: B904

    if format == "json":
        console.print_json(backend.to_dict())
        return

    _print_backend_detail(backend)


def _print_backend_detail(b: BackendInfo) -> None:
    """Print detailed information for a single backend using rich formatting."""
    from rich.panel import Panel
    from rich.rule import Rule

    # Status colour
    status_color = {
        "available": "green",
        "unavailable": "red",
        "deprecated": "yellow",
        "maintenance": "magenta",
    }.get(b.status, "white")

    console.print(Rule(f"[bold cyan]{b.full_id()}[/bold cyan]"))

    # Two-column overview
    overview = [
        f"[bold]Platform:[/bold]  {b.platform.value}",
        f"[bold]Name:[/bold]      {b.name}",
        f"[bold]Type:[/bold]      {'Simulator' if b.is_simulator else 'Hardware'}",
        f"[bold]Qubits:[/bold]    {b.num_qubits or 'N/A'}",
        f"[bold]Status:[/bold]    [{status_color}]{b.status}[/{status_color}]",
    ]
    console.print(Panel("\n".join(overview), title="Overview", box=rich.box.ROUNDED))

    # Fidelity section (only shown if any fidelity data is available)
    fidelity_rows = [
        ("Avg. 1Q Fidelity", b.avg_1q_fidelity, "{:.4f}"),
        ("Avg. 2Q Fidelity", b.avg_2q_fidelity, "{:.4f}"),
        ("Avg. Readout Fidelity", b.avg_readout_fidelity, "{:.4f}"),
        ("Avg. T1 (us)", b.coherence_t1, "{:.3f}"),
        ("Avg. T2 (us)", b.coherence_t2, "{:.3f}"),
    ]
    fidelity_data = [(label, fmt.format(val)) for label, val, fmt in fidelity_rows if val is not None]
    if fidelity_data:
        fidelity_lines = "\n".join(f"[bold]{label}:[/bold]  {val}" for label, val in fidelity_data)
        console.print(Panel(fidelity_lines, title="Fidelity & Coherence", box=rich.box.ROUNDED))

    if b.description:
        console.print(f"\n[bold]Description:[/bold] {b.description}")

    # Topology
    if b.topology:
        from rich.table import Table

        topo_table = Table(title="Qubit Topology (edges)", box=rich.box.SIMPLE)
        topo_table.add_column("Qubit U", justify="right")
        topo_table.add_column("Qubit V", justify="right")
        for edge in b.topology:
            topo_table.add_row(str(edge.u), str(edge.v))
        console.print(topo_table)
    elif not b.is_simulator:
        console.print("\n[dim]Topology: not available from API[/dim]")

    # Extra fields
    if b.extra:
        console.print("\n[bold]Additional Information:[/bold]")
        for key, value in sorted(b.extra.items()):
            if isinstance(value, list):
                if len(value) > 12:
                    value = value[:12] + ["..."]
                display = ", ".join(str(v) for v in value)
            else:
                display = str(value)
            console.print(f"  [cyan]{key}:[/cyan] {display}")


@app.command("chip-display")
def chip_display(
    identifier: str = typer.Argument(
        ...,
        help="Backend identifier in the form 'platform/chip_name' (e.g. originq/wuyuan:d5, ibm/sherbrooke, quafu/ScQ-P18)",
    ),
    update: bool = typer.Option(
        False,
        "--update",
        "-u",
        help="Force-refresh chip data from the cloud before displaying",
    ),
    ai_hints: bool = AI_HINTS_OPTION,
):
    """Show per-qubit chip characterization data for a backend.

    Displays detailed calibration data including: T1/T2 coherence times,
    single-qubit gate fidelity, readout fidelity (R0/R1/avg), and
    two-qubit gate fidelity per connected pair.

    The chip data is cached locally after first fetch. Use --update to
    force-refresh from the cloud.

    Workflow:
      - Pick a backend from: uniqc backend list
      - Force refresh if calibration has been updated: uniqc backend chip-display originq/wuyuan:d5 --update
      - Use this data for qubit selection: see the analyzer module.
    """
    if ai_hints or os.environ.get("UNIQC_AI_HINTS"):
        print_ai_hints("backend-chip-display")

    parts = identifier.split("/", 1)
    if len(parts) != 2:
        print_error("Identifier must be in the form 'platform/chip_name', e.g. originq/wuyuan:d5")
        raise typer.Exit(1) from None

    platform_str, chip_name = parts
    try:
        platform = Platform(platform_str.strip().lower())
    except ValueError:
        print_error(f"Unknown platform '{platform_str}'. Valid: originq, quafu, ibm")
        raise typer.Exit(1) from None

    from uniqc.cli.chip_service import fetch_chip_characterization

    chip = fetch_chip_characterization(chip_name.strip(), platform, force_refresh=update)

    if chip is None:
        print_error(
            f"Chip '{chip_name}' not found on platform '{platform_str}' "
            "or the platform is unavailable (check credentials with: uniqc config validate)"
        )
        raise typer.Exit(1) from None

    _print_chip_detail(chip)


def _fmt(val: float | None, pattern: str) -> str:
    """Format a float or return '-' if None."""
    if val is None:
        return "-"
    return f"{val:{pattern}}"


def _print_chip_detail(chip) -> None:
    """Print chip characterization details using Rich formatting."""
    from rich.panel import Panel
    from rich.rule import Rule
    from rich.table import Table

    console.print(Rule(f"[bold cyan]Chip: {chip.full_id}[/bold cyan]"))

    # Overview panel
    overview = [
        f"[bold]Platform:[/bold]  {chip.platform.value}",
        f"[bold]Chip:[/bold]      {chip.chip_name}",
        f"[bold]Qubits:[/bold]    {len(chip.available_qubits)} available / {len(chip.connectivity)} pairs",
        f"[bold]Calibrated:[/bold] {chip.calibrated_at or 'N/A'}",
    ]
    console.print(Panel("\n".join(overview), title="Overview", box=rich.box.ROUNDED))

    # Global info
    gi = chip.global_info
    if gi.single_qubit_gates or gi.two_qubit_gates or gi.single_qubit_gate_time:
        gi_lines: list[str] = []
        if gi.single_qubit_gates:
            gi_lines.append(f"[bold]1Q Gates:[/bold]     {', '.join(gi.single_qubit_gates)}")
        if gi.two_qubit_gates:
            gi_lines.append(f"[bold]2Q Gates:[/bold]     {', '.join(gi.two_qubit_gates)}")
        if gi.single_qubit_gate_time:
            gi_lines.append(f"[bold]1Q Gate Time:[/bold] {gi.single_qubit_gate_time} ns")
        if gi.two_qubit_gate_time:
            gi_lines.append(f"[bold]2Q Gate Time:[/bold] {gi.two_qubit_gate_time} ns")
        console.print(Panel("\n".join(gi_lines), title="Global Info", box=rich.box.ROUNDED))

    # Per-qubit table
    if chip.single_qubit_data:
        q_table = Table(
            title="Per-Qubit Data",
            box=rich.box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
        )
        q_table.add_column("ID", justify="right", width=5)
        q_table.add_column("T1 (μs)", justify="right", width=9)
        q_table.add_column("T2 (μs)", justify="right", width=9)
        q_table.add_column("1Q Fid.", justify="right", width=9)
        q_table.add_column("R0", justify="right", width=7)
        q_table.add_column("R1", justify="right", width=7)
        q_table.add_column("Avg R", justify="right", width=9)

        for sq in sorted(chip.single_qubit_data, key=lambda x: x.qubit_id):
            q_table.add_row(
                str(sq.qubit_id),
                _fmt(sq.t1, ".2f"),
                _fmt(sq.t2, ".2f"),
                _fmt(sq.single_gate_fidelity, ".4f"),
                _fmt(sq.readout_fidelity_0, ".4f"),
                _fmt(sq.readout_fidelity_1, ".4f"),
                _fmt(sq.avg_readout_fidelity, ".4f"),
            )
        console.print(q_table)

    # Per-pair table
    if chip.two_qubit_data:
        p_table = Table(
            title="Per-Pair 2Q Gate Data",
            box=rich.box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
        )
        p_table.add_column("Qubit U", justify="right", width=8)
        p_table.add_column("Qubit V", justify="right", width=8)
        p_table.add_column("Gate", width=8)
        p_table.add_column("Fidelity", justify="right", width=10)

        for tp in sorted(chip.two_qubit_data, key=lambda x: (x.qubit_u, x.qubit_v)):
            for gate in tp.gates:
                p_table.add_row(
                    str(tp.qubit_u),
                    str(tp.qubit_v),
                    gate.gate,
                    _fmt(gate.fidelity, ".4f"),
                )
        console.print(p_table)


def _format_age(seconds: float) -> str:
    """Return a human-readable age string."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.0f}m"
    hours = minutes / 60
    if hours < 24:
        return f"{hours:.0f}h"
    days = hours / 24
    return f"{days:.0f}d"
