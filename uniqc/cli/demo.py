"""Independent local product demonstration."""

import json
from pathlib import Path
from typing import Annotated

import typer

from uniqc.gateway.demo import DemoRequest, run_demo


def demo(
    case: Annotated[str, typer.Option(help="Local preset: ghz, w, ramsey")] = "ghz",
    qubits: Annotated[int, typer.Option(min=2, max=8, help="Number of qubits")] = 4,
    phase: Annotated[float, typer.Option(help="Ramsey phase in radians")] = 1.5707963267948966,
    output: Annotated[Path | None, typer.Option(help="Write the JSON result")] = None,
):
    """Run a standard circuit with the installed native simulator."""
    try:
        result = run_demo(DemoRequest(case=case, qubits=qubits, phase=phase))
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    text = json.dumps(result, indent=2) + "\n"
    if output:
        output.write_text(text, encoding="utf-8")
    else:
        typer.echo(text, nl=False)
