"""Main CLI entry point for UnifiedQuantum."""

from __future__ import annotations

import sys

import typer

from uniqc import __version__
from uniqc.cli.output import ai_hints_enabled


def _make_cli_streams_loss_tolerant() -> None:
    """Prevent legacy Windows encodings from crashing Rich/Typer output."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(errors="replace")
        except (OSError, ValueError):
            continue


_make_cli_streams_loss_tolerant()

app = typer.Typer(
    name="uniqc",
    help=(
        "UnifiedQuantum CLI — A lightweight quantum computing framework\n"
        "  [link=https://github.com/IAI-USTC-Quantum/UnifiedQuantum]"
        "[cyan]GitHub[/cyan][/link]"
        "  |  "
        "[link=https://iai-ustc-quantum.github.io/UnifiedQuantum/docs/]"
        "[cyan]Documentation[/cyan][/link]\n\n"
        "  Pass --ai-hints/--ai-hint, set UNIQC_AI_HINTS=1, or run "
        "uniqc config always-ai-hint on to show AI workflow guidance.\n"
        "  AI Agent 安装建议：\n"
        "  Codex:  npx skills add IAI-USTC-Quantum/quantum-computing.skill "
        "--agent codex --skill '*'\n"
        "  Claude Code: npx skills add IAI-USTC-Quantum/quantum-computing.skill "
        "--agent claude-code --skill '*'\n\n"
        "  默认按仓库安装本仓库全部 skill（推荐）。"
    ),
    no_args_is_help=True,
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show version and exit",
        is_eager=True,
    ),
    ai_hints: bool = typer.Option(
        False,
        "--ai-hints",
        "--ai-hint",
        help="Show AI workflow hints (also enabled via UNIQC_AI_HINTS=1)",
        is_eager=True,
        hidden=True,
    ),
):
    """UnifiedQuantum CLI - Quantum computing from the command line."""
    if version:
        console = __import__("rich").console.Console()
        console.print(f"[bold cyan]uniqc[/bold cyan] {__version__}")
        raise typer.Exit(0)
    ctx.obj = {"ai_hints": ai_hints_enabled(ai_hints)}


# Import and register subcommands
from uniqc import gateway

from . import backend, calibrate, circuit, doctor, result, simulate, submit, task
from . import config_cmd as config

# Register single-action entrypoints as direct commands instead of sub-groups.
# This avoids Click/Typer group parsing quirks where options after positionals
# are treated as subcommand tokens.
app.command("circuit", help=circuit.HELP)(circuit.convert)
app.command("simulate", help=simulate.HELP)(simulate.simulate)
app.command("submit", help=submit.HELP)(submit.submit)
app.command("result", help=result.HELP)(result.result)
app.command("doctor", help=doctor.HELP)(doctor.run_doctor)
app.add_typer(config.app, name="config")
app.add_typer(task.app, name="task")
app.add_typer(backend.app, name="backend")
app.add_typer(calibrate.app, name="calibrate")
app.add_typer(gateway.app, name="gateway")
