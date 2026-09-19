"""Circuit drawing subcommand: render OriginIR/QASM files as text/svg/png/latex/html."""

from __future__ import annotations

from pathlib import Path

import typer

from .output import (
    AI_HINTS_OPTION,
    ai_hints_enabled,
    print_ai_hints,
    print_error,
    write_output,
)

HELP = "Draw a circuit (text/svg/png/latex/html/interactive)"
INPUT_FILE_ARGUMENT = typer.Argument(..., help="Input circuit file (OriginIR or OpenQASM)", exists=True)
MODE_OPTION = typer.Option("text", "--mode", "-m", help="text | svg | png | mpl | latex | html | interactive")
STYLE_OPTION = typer.Option("quantikz", "--style", "-s", help="quantikz | qiskit | modern | print")
FOLD_OPTION = typer.Option("auto", "--fold", help="Gates per row: auto | int | 0 (disable)")
OUTPUT_OPTION = typer.Option(None, "--output", "-o", help="Output file (default: stdout for text/latex/svg)")
THEME_OPTION = typer.Option("light", "--theme", help="light | dark")
ORIENTATION_OPTION = typer.Option("h", "--orientation", help="h (time→) | v (time↓)")
PARAM_OPTION = typer.Option("pi", "--param-mode", help="pi | decimal | symbol | hidden")
CLBITS_OPTION = typer.Option(False, "--show-clbits", help="Draw classical double-line wires")
UNICODE_OPTION = typer.Option(False, "--unicode", "-u", help="Use Unicode symbols in text mode (default: ASCII)")


def draw(
    input_file: Path = INPUT_FILE_ARGUMENT,
    mode: str = MODE_OPTION,
    style: str = STYLE_OPTION,
    fold: str = FOLD_OPTION,
    output: Path | None = OUTPUT_OPTION,
    theme: str = THEME_OPTION,
    orientation: str = ORIENTATION_OPTION,
    param_mode: str = PARAM_OPTION,
    show_clbits: bool = CLBITS_OPTION,
    unicode: bool = UNICODE_OPTION,
    ai_hints: bool = AI_HINTS_OPTION,
):
    """Render a circuit file in the given mode.

    Examples:
      uniqc draw bell.originir                      # ASCII art to stdout
      uniqc draw bell.originir -m svg -o bell.svg   # vector image
      uniqc draw bell.originir -m png -o bell.png   # raster image
      uniqc draw bell.originir -m latex             # quantikz source
    """
    if ai_hints_enabled(ai_hints):
        print_ai_hints("circuit")

    from uniqc.visualization import render

    content = input_file.read_text(encoding="utf-8")
    fold_value: object = fold
    if fold != "auto":
        try:
            fold_value = int(fold)
        except ValueError:
            print_error(f"--fold must be 'auto' or an integer, got {fold!r}")
            raise typer.Exit(1) from None

    try:
        result = render(
            content,
            mode=mode,
            style=style,
            fold=fold_value,
            orientation=orientation,
            theme=theme,
            param_mode=param_mode,
            show_clbits=show_clbits,
            charset="unicode" if unicode else "ascii",
            filename=str(output) if output else None,
        )
    except ValueError as exc:
        print_error(str(exc))
        raise typer.Exit(1) from None

    if output:
        return
    if isinstance(result, bytes):
        print_error("PNG output requires --output (-o).")
        raise typer.Exit(1)
    write_output(str(result), None)
