"""Main CLI entry point for UnifiedQuantum."""

from __future__ import annotations

import os

import typer

app = typer.Typer(
    name="uniqc",
    help=(
        "UnifiedQuantum CLI — A lightweight quantum computing framework\n"
        "  [link=https://github.com/IAI-USTC-Quantum/UnifiedQuantum]"
        "[cyan]GitHub[/cyan][/link]"
        "  |  "
        "[link=https://iai-ustc-quantum.github.io/UnifiedQuantum/]"
        "[cyan]Documentation[/cyan][/link]\n\n"
        "  Pass --ai-hints (or set UNIQC_AI_HINTS=1) to any command to show "
        "AI workflow guidance."
    ),
    no_args_is_help=True,
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    ai_hints: bool = typer.Option(
        False,
        "--ai-hints",
        help="Show AI workflow hints (also enabled via UNIQC_AI_HINTS=1)",
        is_eager=True,
        hidden=True,
    ),
):
    """UnifiedQuantum CLI - Quantum computing from the command line."""
    ctx.obj = {"ai_hints": ai_hints or bool(os.environ.get("UNIQC_AI_HINTS"))}


# Import and register subcommands
from . import backend
from . import circuit
from . import simulate
from . import submit
from . import result
from . import config_cmd as config
from . import task

# Register single-action entrypoints as direct commands instead of sub-groups.
# This avoids Click/Typer group parsing quirks where options after positionals
# are treated as subcommand tokens.
app.command("circuit", help=circuit.HELP)(circuit.convert)
app.command("simulate", help=simulate.HELP)(simulate.simulate)
app.command("submit", help=submit.HELP)(submit.submit)
app.command("result", help=result.HELP)(result.result)
app.add_typer(config.app, name="config")
app.add_typer(task.app, name="task")
app.add_typer(backend.app, name="backend")
