"""Gateway management CLI: start / stop / restart / status."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from contextlib import suppress

import typer
from rich.console import Console

from uniqc.backend_adapter.task.store import DEFAULT_CACHE_DIR
from uniqc.gateway.config import (
    load_gateway_config,
    save_gateway_config,
)

app = typer.Typer(
    help="Manage the uniqc gateway web UI server.",
    no_args_is_help=True,
)

console = Console()

PID_FILE = DEFAULT_CACHE_DIR / "gateway.pid"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_pid() -> int | None:
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text().strip())
    except (ValueError, OSError):
        return None


def _write_pid(pid: int) -> None:
    DEFAULT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(pid))


def _clear_pid() -> None:
    if PID_FILE.exists():
        try:
            PID_FILE.unlink(missing_ok=True)
        except OSError as exc:
            console.print(f"[yellow]Warning: failed to clear stale gateway pid file {PID_FILE}: {exc}[/yellow]")


def _is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _resolve_uvicorn_cmd(host: str, port: int) -> list[str]:
    """Return the command to start uvicorn.

    Tries 'uv run' first, but only if uvicorn is actually available
    in that environment; otherwise falls back to sys.executable directly.
    """
    base_cmd = [
        sys.executable, "-m", "uvicorn",
        "uniqc.gateway.server:create_app",
        "--factory",
        "--host", host,
        "--port", str(port),
    ]
    # Only use 'uv run' if uv is present AND uvicorn is available in it
    try:
        cp = subprocess.run(
            ["uv", "run", "--no-project", "python", "-c", "import uvicorn"],
            capture_output=True, check=False,
        )
        if cp.returncode == 0:
            return ["uv", "run", "--no-project", "--", *base_cmd]
    except FileNotFoundError:
        pass
    return base_cmd


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@app.command()
def start(
    port: int | None = typer.Option(
        None, "--port", "-p", help="Port to listen on (overrides config.yaml)"
    ),
    host: str | None = typer.Option(
        None, "--host", help="Host to bind to (overrides config.yaml)"
    ),
) -> None:
    """Start the gateway web UI server in the background."""
    cfg = load_gateway_config()
    host = host or cfg["host"]
    port = port or cfg["port"]

    # Persist if changed
    if host != cfg["host"] or port != cfg["port"]:
        save_gateway_config(host=host, port=port)

    # Check if already running
    pid = _read_pid()
    if pid is not None and _is_alive(pid):
        console.print(f"[yellow]Gateway is already running (PID {pid}) at http://{host}:{port}[/yellow]")
        raise typer.Exit(0)

    _clear_pid()

    # Write config banner
    console.print(f"[cyan]Starting uniqc gateway[/cyan] at http://{host}:{port}")
    console.print("[dim]Press Ctrl+C to stop the server, or use: uniqc gateway stop[/dim]")

    cmd = _resolve_uvicorn_cmd(host, port)

    # Start in background — redirect stdout/stderr to a log file
    log_dir = DEFAULT_CACHE_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "gateway.log"

    with open(log_file, "w") as fh:
        proc = subprocess.Popen(
            cmd,
            stdout=fh,
            stderr=subprocess.STDOUT,
            # Detach from controlling TTY so Ctrl+C on the parent shell
            # doesn't kill the background server.
            start_new_session=True,
        )

    _write_pid(proc.pid)

    console.print(f"[green]Gateway started (PID {proc.pid})[/green]")
    console.print(f"[dim]Log: {log_file}[/dim]")
    console.print(f"[bold]Open:[/bold] http://{host}:{port}")


@app.command()
def stop() -> None:
    """Stop the running gateway server."""
    pid = _read_pid()
    if pid is None or not _is_alive(pid):
        _clear_pid()
        console.print("[yellow]Gateway is not running.[/yellow]")
        raise typer.Exit(0)

    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as e:
        console.print(f"[red]Failed to kill PID {pid}: {e}[/red]")

    _clear_pid()
    console.print(f"[green]Gateway stopped (PID {pid}).[/green]")


@app.command()
def restart(
    port: int | None = typer.Option(None, "--port", "-p"),
    host: str | None = typer.Option(None, "--host"),
) -> None:
    """Stop and restart the gateway server."""
    # Find current settings before stopping
    pid = _read_pid()
    if pid is not None and _is_alive(pid):
        _clear_pid()
        with suppress(OSError):
            os.kill(pid, signal.SIGTERM)
        console.print(f"[dim]Stopped previous instance (PID {pid}).[/dim]")

    # Re-use previously saved host/port
    cfg = load_gateway_config()
    host = host or cfg["host"]
    port = port or cfg["port"]

    # Temporarily override config so start() uses these values
    save_gateway_config(host=host, port=port)
    start(port=port, host=host)


@app.command("status")
def status() -> None:
    """Check whether the gateway server is running."""
    pid = _read_pid()
    cfg = load_gateway_config()
    host = cfg["host"]
    port = cfg["port"]

    if pid is not None and _is_alive(pid):
        console.print(f"[green]Gateway is running[/green] (PID {pid})")
        console.print(f"  URL:   http://{host}:{port}")
        console.print(f"  Config port: {port}  host: {host}")
    else:
        if pid is not None:
            _clear_pid()
        console.print("[yellow]Gateway is not running.[/yellow]")
        console.print("  Run: uniqc gateway start")
