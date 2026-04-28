"""Main CLI entry point for UnifiedQuantum."""

from __future__ import annotations

import typer

app = typer.Typer(
    name="uniqc",
    help="UnifiedQuantum - A lightweight quantum computing framework",
    no_args_is_help=True,
)


@app.callback()
def main():
    """UnifiedQuantum CLI - Quantum computing from the command line."""
    pass


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
