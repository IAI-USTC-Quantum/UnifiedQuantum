"""Quantum circuit visualization tools.

.. deprecated::
    The module-level ``draw`` / ``draw_html`` wrappers are deprecated in favor
    of :func:`uniqc.visualization.render` (or equivalently
    ``Circuit.draw(...)``), which offer self-developed text art (no pyqpanda3
    dependency), SVG/PNG/LaTeX/HTML/interactive modes, styles, folding, and
    full OriginIR-ext coverage.  The wrappers will be removed in uniqc 0.2.0.
"""

__all__ = ["draw", "draw_html"]

from uniqc._deprecation import warn_removed_in_0_2_0


def draw(ir_str, language="OriginIR"):
    """Draw the circuit in text format.  Deprecated — use ``render(mode="text")``.

    Args:
        ir_str (str): The input circuit in OriginIR or QASM format.
        language (str): Deprecated. The language is now auto-detected from
            the content (``QINIT``/``OPENQASM`` headers).

    Returns:
        TextDrawing: The rendered ASCII drawing (also printed for
        backwards compatibility).
    """
    warn_removed_in_0_2_0(
        "uniqc.visualization.draw()",
        replacement="uniqc.visualization.render(circuit, mode='text')",
        detail="The pyqpanda3 delegate is gone: text art is now self-developed, "
        "the input language is auto-detected, and the drawing string is returned "
        "instead of a pyqpanda3 QProg.",
    )
    from .circuit_render import render

    art = render(ir_str, mode="text")
    print(art)
    return art


def draw_html(ir_str, language="OriginIR", output_path=None, *, title="Quantum circuit"):
    """Render a static HTML/SVG circuit diagram.  Deprecated — use ``render(mode="html")``.

    Args:
        ir_str (str): The input circuit in OriginIR or QASM format.
        language (str): Deprecated. Auto-detected from content.
        output_path: Optional path to write the HTML document to.
        title: Ignored (kept for signature compatibility).

    Returns:
        str: The self-contained HTML document.
    """
    warn_removed_in_0_2_0(
        "uniqc.visualization.draw_html()",
        replacement="uniqc.visualization.render(circuit, mode='html')",
    )
    from .circuit_render import render

    return render(ir_str, mode="html", filename=output_path)
