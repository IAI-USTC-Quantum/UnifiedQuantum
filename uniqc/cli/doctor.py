"""Diagnostic subcommand — verify uniqc installation health."""

from __future__ import annotations

import contextlib
import platform
import sqlite3
import sys
from pathlib import Path
from typing import Any

import rich.box
from rich.table import Table

from .output import (
    AI_HINTS_OPTION,
    ai_hints_enabled,
    build_ref_str,
    console,
    print_ai_hints,
)

HELP = f"Run diagnostics to verify your uniqc installation\n  {build_ref_str('doctor')}"

# ---------------------------------------------------------------------------
# Dependency groups — {group_label: [package_name, ...]}
# ---------------------------------------------------------------------------
_DEPENDENCY_GROUPS: list[tuple[str, list[str]]] = [
    ("originq", ["pyqpanda3"]),
    ("quafu", ["pyquafu"]),
    ("quark", ["quarkstudio", "quarkcircuit"]),
    ("qiskit", ["qiskit", "qiskit_ibm_runtime"]),
    ("simulation", ["qutip"]),
    ("visualization", ["matplotlib"]),
    ("pytorch", ["torch"]),
]

_CORE_DEPS = ["numpy", "typer", "rich", "scipy", "yaml"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mask_key(key: str) -> str:
    return "****"


def _import_version(pkg: str) -> str:
    try:
        mod = __import__(pkg)
        return getattr(mod, "__version__", "installed")
    except ImportError:
        return "not installed"


# ---------------------------------------------------------------------------
# Check functions — each prints a Rich section and returns nothing.
# ---------------------------------------------------------------------------


def _check_environment() -> None:
    from uniqc import __version__
    from uniqc.config import CONFIG_FILE

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("key", style="bold")
    table.add_column("value")
    table.add_row("uniqc", __version__)
    table.add_row("Python", f"{sys.version}  ({platform.python_implementation()})")
    table.add_row("OS", platform.platform())
    table.add_row("Config", str(CONFIG_FILE))
    console.print(table)


def _check_dependencies() -> None:
    # Core deps
    table = Table(title="Core Dependencies", box=rich.box.ROUNDED, show_lines=False)
    table.add_column("Package", style="bold")
    table.add_column("Version")
    for pkg in _CORE_DEPS:
        ver = _import_version(pkg)
        style = "green" if ver != "not installed" else "red"
        table.add_row(pkg, f"[{style}]{ver}[/{style}]")
    console.print(table)

    # Optional groups
    table = Table(title="Optional Dependencies", box=rich.box.ROUNDED, show_lines=False)
    table.add_column("Group", style="bold")
    table.add_column("Package")
    table.add_column("Version")
    for group, packages in _DEPENDENCY_GROUPS:
        for i, pkg in enumerate(packages):
            ver = _import_version(pkg)
            style = "green" if ver != "not installed" else "dim"
            label = group if i == 0 else ""
            table.add_row(label, pkg, f"[{style}]{ver}[/{style}]")
    console.print(table)


def _check_config() -> None:
    from uniqc.config import (
        CONFIG_FILE,
        SUPPORTED_PLATFORMS,
        get_active_profile,
        load_config,
        validate_config,
    )

    # File existence
    if not CONFIG_FILE.exists():
        console.print(f"[red]✗[/red] Config file not found: {CONFIG_FILE}")
        console.print("[dim]  Run `uniqc config init` to create one.[/dim]")
        return

    console.print(f"[green]✓[/green] Config file: {CONFIG_FILE}")

    # Validate
    errors = validate_config()
    if not errors:
        console.print("[green]✓[/green] Configuration is valid")
    else:
        for err in errors:
            if err.startswith("Warning:"):
                console.print(f"[yellow]⚠[/yellow] {err}")
            else:
                console.print(f"[red]✗[/red] {err}")

    # Active profile
    try:
        profile = get_active_profile()
        console.print(f"  Active profile: [cyan]{profile}[/cyan]")
    except Exception as exc:
        console.print(f"[red]✗[/red] Could not determine active profile: {exc}")
        return

    # Per-platform credentials
    cfg: dict[str, Any] = {}
    with contextlib.suppress(Exception):
        cfg = load_config()

    profile_cfg = cfg.get(profile, {}) if isinstance(cfg, dict) else {}

    table = Table(title="Platform Credentials", box=rich.box.ROUNDED, show_lines=False)
    table.add_column("Platform", style="bold")
    table.add_column("Token/Key")
    table.add_column("Status")
    for plat in SUPPORTED_PLATFORMS:
        plat_cfg = profile_cfg.get(plat, {})
        if not isinstance(plat_cfg, dict):
            plat_cfg = {}
        if plat == "quark":
            raw = plat_cfg.get("QUARK_API_KEY", "") or plat_cfg.get("token", "")
        else:
            raw = plat_cfg.get("token", "")
        if raw:
            masked = _mask_key(raw)
            table.add_row(plat, masked, "[green]configured[/green]")
        else:
            table.add_row(plat, "[dim]—[/dim]", "[yellow]not set[/yellow]")
    console.print(table)


def _check_task_db() -> None:
    from uniqc.backend_adapter.task.store import (
        APPLICATION_ID,
        DB_FILENAME,
        DEFAULT_CACHE_DIR,
    )

    db_path: Path = DEFAULT_CACHE_DIR / DB_FILENAME

    if not db_path.exists():
        console.print(f"[yellow]⚠[/yellow] Task database not found: {db_path}")
        console.print("[dim]  It will be created automatically on first task submission.[/dim]")
        return

    console.print(f"[green]✓[/green] Task database: {db_path}")

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            app_id = conn.execute("PRAGMA application_id").fetchone()[0]
            if app_id == APPLICATION_ID:
                console.print(f"[green]✓[/green] application_id: 0x{app_id:08X} (UNIC)")
            else:
                console.print(f"[red]✗[/red] application_id: 0x{app_id:08X}, expected 0x{APPLICATION_ID:08X} (UNIC)")

            schema_ver = conn.execute("PRAGMA user_version").fetchone()[0]
            console.print(f"  Schema version: {schema_ver}")

            row = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()
            count = row[0] if row else 0
            console.print(f"  Task count: {count}")
        finally:
            conn.close()
    except Exception as exc:
        console.print(f"[red]✗[/red] Failed to read task database: {exc}")


def _check_backend_cache() -> None:
    from uniqc.backend_adapter.backend_cache import cache_info

    info = cache_info()
    if not info:
        console.print("[yellow]⚠[/yellow] Backend cache is empty")
        console.print("[dim]  Run `uniqc backend update` to populate.[/dim]")
        return

    console.print("[green]✓[/green] Backend cache exists")
    table = Table(title="Backend Cache", box=rich.box.ROUNDED, show_lines=False)
    table.add_column("Platform", style="bold")
    table.add_column("Backends")
    table.add_column("Age")
    table.add_column("Stale?")
    for plat, meta in info.items():
        age_s = meta.get("age_seconds", 0)
        if age_s < 3600:
            age_str = f"{age_s:.0f}s"
        elif age_s < 86400:
            age_str = f"{age_s / 3600:.1f}h"
        else:
            age_str = f"{age_s / 86400:.1f}d"
        stale = meta.get("is_stale", True)
        stale_str = "[yellow]yes[/yellow]" if stale else "[green]no[/green]"
        table.add_row(plat, str(meta.get("num_backends", 0)), age_str, stale_str)
    console.print(table)


def _check_platform_connectivity() -> None:
    from uniqc.backend_adapter.backend_info import Platform
    from uniqc.backend_adapter.backend_registry import fetch_platform_backends
    from uniqc.cli.chip_service import fetch_chip_characterization
    from uniqc.config import SUPPORTED_PLATFORMS, has_platform_credentials

    configured_platforms = [
        p for p in SUPPORTED_PLATFORMS if p != Platform.QUAFU.value and has_platform_credentials(p)
    ]

    if not configured_platforms:
        console.print("[yellow]⚠[/yellow] No platform credentials configured — skipping connectivity check")
        return

    for plat_str in configured_platforms:
        plat = Platform(plat_str)
        console.print(f"\n[bold]Platform: {plat_str}[/bold]")

        # Fetch backends (tests credentials + network)
        try:
            backends, fetched = fetch_platform_backends(plat, force_refresh=True)
            console.print(f"[green]✓[/green] Connectivity OK — {len(backends)} backend(s) fetched")
        except Exception as exc:
            console.print(f"[red]✗[/red] Failed to fetch backends: {exc}")
            continue

        # Check calibration data for hardware backends
        hw_backends = [b for b in backends if not b.is_simulator]
        if not hw_backends:
            console.print("  No hardware backends — skipping calibration check")
            continue

        for be in hw_backends:
            try:
                chip = fetch_chip_characterization(be.name, plat, force_refresh=True)
            except Exception as exc:
                console.print(f"  [red]✗[/red] {be.name}: calibration fetch failed — {exc}")
                continue

            if chip is None:
                console.print(f"  [yellow]⚠[/yellow] {be.name}: no characterization data")
                continue

            issues: list[str] = []
            if not chip.available_qubits:
                issues.append("empty available_qubits")
            if not chip.connectivity:
                issues.append("empty connectivity")
            if not chip.single_qubit_data:
                issues.append("empty single_qubit_data")
            if not chip.two_qubit_data:
                issues.append("empty two_qubit_data")

            if issues:
                detail = ", ".join(issues)
                console.print(f"  [yellow]⚠[/yellow] {be.name}: {detail}")
            else:
                cal = chip.calibrated_at or "unknown"
                console.print(f"  [green]✓[/green] {be.name}: calibration OK (calibrated_at={cal})")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_doctor(
    ai_hints: bool = AI_HINTS_OPTION,
) -> None:
    """Run diagnostics to verify your uniqc installation and configuration."""
    if ai_hints_enabled(ai_hints):
        print_ai_hints("doctor")

    sections: list[tuple[str, object]] = [
        ("1. Environment & Version", _check_environment),
        ("2. Dependencies", _check_dependencies),
        ("3. Config File", _check_config),
        ("4. Task Database", _check_task_db),
        ("5. Backend Cache", _check_backend_cache),
        ("6. Platform Connectivity & Calibration", _check_platform_connectivity),
    ]

    for title, fn in sections:
        console.print()
        console.rule(f"[bold cyan]{title}[/bold cyan]")
        fn()

    console.print()
    console.rule("[bold cyan]Done[/bold cyan]")
    console.print()
