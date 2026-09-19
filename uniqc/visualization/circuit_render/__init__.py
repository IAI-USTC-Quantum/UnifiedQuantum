"""Circuit rendering: one entry point, seven output modes.

``render()`` / :meth:`uniqc.circuit_builder.Circuit.draw` are thin, equivalent
wrappers around the same core (per the design-review decision).

Modes: ``text`` (self-developed ASCII/Unicode art — no pyqpanda3 needed),
``svg``, ``png``, ``mpl``, ``latex`` (quantikz source), ``html`` (static,
self-contained), ``interactive`` (HTML + click-to-inspect).

The core modes (text/svg/latex/html/interactive) are pure-stdlib.  ``png``
prefers ``cairosvg`` and falls back to ``matplotlib``; ``mpl`` requires
``matplotlib``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .model import DrawCircuit, to_draw_circuit
from .options import MODES, RenderOptions

__all__ = ["render", "TextDrawing", "MODES"]


class TextDrawing(str):
    """``str`` subclass whose REPL display is the drawing itself (qiskit-style)."""

    def __repr__(self) -> str:  # pragma: no cover - display nicety
        return str(self)


def _smart_default_mode() -> str:
    """terminal -> text; Jupyter notebook -> svg rich display."""
    try:
        from IPython import get_ipython

        shell = get_ipython()
        if shell is not None and type(shell).__name__ == "ZMQInteractiveShell":
            return "svg"
    except Exception:
        pass
    return "text"


def render(
    circuit: Any,
    mode: str | None = None,
    *,
    style: str = "quantikz",
    fold: object = "auto",
    orientation: str = "h",
    qubit_order: str = "asc",
    theme: str = "light",
    param_mode: str = "pi",
    show_clbits: bool = False,
    charset: str = "ascii",
    scale: float = 100,
    filename: str | Path | None = None,
):
    """Render a quantum circuit.

    Args:
        circuit: A :class:`~uniqc.circuit_builder.Circuit`, an OriginIR(-ext)
            or OpenQASM 2.0 string, or a JSON list of gate dicts.
        mode: ``None`` (smart default: terminal→``text``, Jupyter→``svg``),
            or one of ``text/svg/png/mpl/latex/html/interactive``.
        style: ``quantikz`` (default) | ``qiskit`` | ``modern`` | ``print``.
        fold: gates per row — ``"auto"`` (terminal width for text, 16
            otherwise), an int, or ``0`` to disable folding.
        orientation: ``"h"`` (time→) or ``"v"`` (time↓, graphical modes only).
        qubit_order: ``"asc"`` (q0 on top, default) or ``"desc"``.
        theme: ``"light"`` | ``"dark"``.
        param_mode: ``"pi"`` (π-fractions, default) | ``"decimal"`` |
            ``"symbol"`` | ``"hidden"``.
        show_clbits: draw classical double-line wires (default ``False``).
        charset: ``"ascii"`` (default) | ``"unicode"`` for ``text`` mode.
        scale: percent scaling for graphical modes.
        filename: when given, also write the output to this path.

    Returns:
        ``text``/``svg``/``latex``/``html``/``interactive`` → ``str``
        (``text`` returns a :class:`TextDrawing` whose repr is the art);
        ``png`` → ``bytes``; ``mpl`` → ``matplotlib.figure.Figure``.
    """
    mode = mode or _smart_default_mode()
    if mode == "ascii":  # convenience alias
        mode = "text"
    if mode not in MODES:
        raise ValueError(f"Unknown draw mode {mode!r}. Available: {', '.join(MODES)} (plus 'ascii' alias).")
    opts = RenderOptions(
        mode=mode,
        style=style,
        fold=fold,
        orientation=orientation,
        qubit_order=qubit_order,
        theme=theme,
        param_mode=param_mode,
        show_clbits=show_clbits,
        charset=charset,
        scale=scale,
    )
    draw: DrawCircuit = to_draw_circuit(circuit)

    if mode == "text":
        from .text import render_text

        result: Any = TextDrawing(render_text(draw, opts))
    elif mode == "svg":
        from .svg import render_svg

        result = render_svg(draw, opts)[0]
    elif mode == "latex":
        from .latex import render_latex

        result = render_latex(draw, opts)
    elif mode == "html":
        from .html import render_html

        result = render_html(draw, opts, interactive=False)
    elif mode == "interactive":
        from .html import render_html

        result = render_html(draw, opts, interactive=True)
    elif mode == "mpl":
        from .mpl import render_mpl

        result = render_mpl(draw, opts)
    else:  # png
        from .mpl import render_png_bytes

        result = render_png_bytes(draw, opts)

    if filename is not None:
        path = Path(filename)
        if mode == "png":
            path.write_bytes(result)
        elif mode == "mpl":
            result.savefig(path, bbox_inches="tight")
        else:
            path.write_text(str(result), encoding="utf-8")
    return result
