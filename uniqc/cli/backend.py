"""``uniqc backend`` CLI subcommand."""

from __future__ import annotations

import sys

import rich.box
import typer

from uniqc.backend_cache import cache_info, invalidate_all
from uniqc.backend_info import BackendInfo, Platform
from uniqc.backend_registry import fetch_all_backends, fetch_platform_backends, find_backend
from uniqc.cli.output import (
    console,
    print_error,
    print_info,
    print_success,
    print_warning,
)

app = typer.Typer(help="List, update, and inspect quantum cloud backends")


# Detect whether a subcommand was given by checking if the first
# positional arg in sys.argv matches a known subcommand name.
_SUB_COMMANDS = frozenset({"list", "update", "show"})


def _subcommand_given() -> bool:
    args = sys.argv
    # e.g. ['uniqc', 'backend', 'list', ...] → index 2 is the subcommand
    if len(args) >= 3 and args[1] == "backend":
        return args[2] in _SUB_COMMANDS
    return False


@app.callback(invoke_without_command=True)
def backend(
    show: str | None = typer.Option(
        None, "--show", "-s",
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


@app.command("list")
def list_backends(
    platform: str | None = typer.Option(
        None, "--platform", "-p",
        help="Only show backends for this platform (originq/quafu/ibm)",
    ),
    status_filter: str | None = typer.Option(
        None, "--status", "-s",
        help="Filter by status: available, unavailable, deprecated, simulator, hardware",
    ),
    format: str = typer.Option(
        "table", "--format", "-f",
        help="Output format: table (default) or json",
    ),
):
    """List all available backends from configured platforms.

    Backend data is cached for 24 hours. Use ``uniqc backend update`` to
    force-refresh.
    """
    target_platform: Platform | None = None
    if platform:
        try:
            target_platform = Platform(platform.lower())
        except ValueError:
            print_error(
                f"Unknown platform '{platform}'. "
                f"Valid: {', '.join(p.value for p in Platform)}"
            )
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

    # Apply status filter
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
        return True

    # Build output rows
    rows: list[list[str]] = []
    json_data: list[dict] = []
    for plat, backends in all_backends.items():
        for b in backends:
            if not matches_filter(b):
                continue
            rows.append([
                plat.value,
                b.name,
                str(b.num_qubits) if b.num_qubits else "-",
                b.status,
                "sim" if b.is_simulator else "hw",
            ])
            json_data.append(b.to_dict())

    if format == "json":
        console.print_json(json_data)
        return

    if not rows:
        print_warning(f"No backends match filter '--status {status_filter}'")
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
    info = cache_info()
    if info:
        lines = []
        for p, meta in info.items():
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
        None, "--platform", "-p",
        help="Only update backends for this platform (originq/quafu/ibm)",
    ),
    clear: bool = typer.Option(
        False, "--clear", "-c",
        help="Clear cache before updating (force re-fetch all platforms)",
    ),
):
    """Force-refresh backend information from cloud APIs.

    By default, ``uniqc backend list`` caches results for 24 hours.
    Use this command to fetch fresh data immediately.
    """

    if clear:
        invalidate_all()
        print_info("Cache cleared.")

    targets = [Platform(platform.lower())] if platform else list(Platform)
    updated_platforms: list[str] = []
    warnings_list: list[str] = []

    for plat in targets:
        try:
            backends, fresh = fetch_platform_backends(plat, force_refresh=True)
            if fresh:
                updated_platforms.append(f"{plat.value} ({len(backends)} backends)")
            else:
                print_warning(f"{plat.value}: no new data available")
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
):
    """Show detailed information for a specific backend.

    Examples::

        uniqc backend show originq:HanYuan_01
        uniqc backend show quafu:ScQ-P10
        uniqc backend show ibm:ibmq_qasm_simulator
    """
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
