"""Render option container shared by all circuit-drawing modes."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["RenderOptions", "MODES"]

MODES = ("text", "svg", "png", "mpl", "latex", "html", "interactive")


@dataclass
class RenderOptions:
    """Drawing options; defaults follow the design-review decisions.

    - style: ``quantikz`` (default) | ``qiskit`` | ``modern`` | ``print``
    - fold: gates per row — ``"auto"`` (terminal width for text, 16 for
      graphical modes), an int, or ``0``/``None``-ish to disable
    - orientation: ``"h"`` (time flows right) or ``"v"`` (time flows down)
    - qubit_order: ``"asc"`` (q0 on top) or ``"desc"``
    - theme: ``"light"`` | ``"dark"``
    - param_mode: ``"pi"`` (π/4 form) | ``"decimal"`` | ``"symbol"`` | ``"hidden"``
    - show_clbits: draw classical double-line wires (default off)
    - charset: ``"ascii"`` (default) | ``"unicode"`` for the text mode
    - scale: percent scaling for graphical modes
    """

    mode: str | None = None
    style: str = "quantikz"
    fold: object = "auto"
    orientation: str = "h"
    qubit_order: str = "asc"
    theme: str = "light"
    param_mode: str = "pi"
    show_clbits: bool = False
    charset: str = "ascii"
    scale: float = 100

    @property
    def vertical(self) -> bool:
        return self.orientation == "v"
