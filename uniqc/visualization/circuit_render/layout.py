"""Column layout engine for circuit rendering (shared by all output modes).

An ASAP (as-soon-as-possible) greedy layering assigns every op a column:
each op lands on the first column where all of its lanes (qubit wires, cbit
lanes, and for control-flow markers *every* lane) are free.  Column widths are
content-driven; the columns may then be folded into bands (rows of the final
figure) according to a per-mode fold policy.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field

from .labels import classify, cop_label, label_lines
from .model import FLOW_OPS, DrawCircuit, DrawOp

__all__ = ["Layout", "FlowSpan", "layout_circuit", "estimate_text_width"]


@dataclass
class FlowSpan:
    """A QIF/ENDQIF or QWHILE/ENDQWHILE bracket, in column coordinates."""

    kind: str  # "QIF" | "QWHILE"
    cond: str
    col_begin: int
    col_end: int


@dataclass
class Layout:
    """Laid-out circuit: ops carry ``col``; bands fold columns into rows."""

    ops: list[DrawOp]
    n_cols: int
    col_widths: list[float]
    spans: list[FlowSpan] = field(default_factory=list)
    bands: list[tuple[int, int]] = field(default_factory=list)  # inclusive col ranges


def estimate_text_width(text: str, font_size: float) -> float:
    """Heuristic text width (px) — mirrors what the SVG browser render shows."""
    w = 0.0
    for ch in text:
        cp = ord(ch)
        w += font_size * (0.95 if 0x2000 < cp < 0x3300 or cp > 0x2E7F else 0.62)
    return w


def _lane_keys(op: DrawOp, n_qubits: int, n_cbits: int) -> list[str]:
    if op.op == "COP":
        return [f"c:{c}" for c in op.cbits]
    if op.op in FLOW_OPS:
        # Control-flow brackets span the whole figure: they must occupy every
        # lane so they are placed after all preceding content.
        return [f"q:{q}" for q in range(n_qubits)] + [f"c:{c}" for c in range(n_cbits)]
    keys = [f"q:{q}" for q in op.qubits]
    if op.op == "MEASURE":
        keys += [f"c:{c}" for c in op.cbits]
    keys += [f"q:{q}" for q in op.controls]
    return keys


def _assign_columns(draw: DrawCircuit) -> list[FlowSpan]:
    next_free: dict[str, int] = {}
    n_cols = 0
    for op in draw.ops:
        keys = _lane_keys(op, draw.n_qubits, draw.n_cbits)
        col = max((next_free.get(k, 0) for k in keys), default=0)
        op.col = col
        for k in keys:
            next_free[k] = col + 1
        n_cols = max(n_cols, col + 1)
    spans: list[FlowSpan] = []
    stack: list[DrawOp] = []
    for op in draw.ops:
        if op.op in ("QIF", "QWHILE"):
            stack.append(op)
        elif op.op in ("ENDIF", "ENDWHILE") and stack:
            begin = stack.pop()
            spans.append(FlowSpan(kind=begin.op, cond=begin.cond or "", col_begin=begin.col, col_end=op.col))
    return spans


_SYMBOL_OPS = {"CNOT", "CX", "CZ", "CP", "CU1", "P", "SWAP", "TOFFOLI", "CCX", "CCNOT", "CSWAP", "FREDKIN"}


def _column_widths(draw: DrawCircuit, geom, param_mode: str) -> list[float]:
    widths: list[float] = []
    for op in draw.ops:
        kind = classify(op)
        if op.op == "BARRIER":
            w = 22.0
        elif op.op in FLOW_OPS:
            w = 14.0
        elif kind == "measure":
            w = max(48.0, geom.min_col)
        elif kind == "cop":
            w = estimate_text_width(cop_label(op), geom.fs) + 18
        elif op.op.upper() in _SYMBOL_OPS and not op.controls:
            w = min(52.0, max(38.0, geom.min_col * 0.8))
        else:
            name, params = label_lines(op, param_mode)
            w = (
                max(
                    estimate_text_width(name, geom.fs),
                    estimate_text_width(params, geom.pfs) if params else 0.0,
                )
                + geom.pad
            )
            if op.op == "QRAM":
                w = estimate_text_width("QRAM", geom.fs) + 44
            elif op.op == "DEF":
                w = max(w, estimate_text_width(f"DEF {op.name}", geom.fs) + 30)
            elif op.op == "CHANNEL":
                w = max(w, 34.0)
        while op.col >= len(widths):
            widths.append(geom.min_col)
        if w > widths[op.col]:
            widths[op.col] = w
    return widths


def resolve_fold(fold, mode: str, n_cols: int) -> int:
    """Resolve the ``fold`` option to a concrete column count (0 = no fold).

    ``fold="auto"``: for text output, fit the current terminal width; for
    graphical outputs (no fixed viewport) fold at 16 columns.  ``fold=None``
    is treated as ``"auto"``; an int ``<= 0`` disables folding.
    """
    if fold is None or fold == "auto":
        if mode == "text":
            term_cols = shutil.get_terminal_size(fallback=(110, 24)).columns
            # ~7 characters per layout column is a good average density
            return max(4, min(n_cols, (term_cols - 8) // 7))
        return 16 if n_cols > 16 else 0
    fold = int(fold)
    return fold if fold > 0 else 0


def layout_circuit(draw: DrawCircuit, geom, param_mode: str, fold, mode: str = "svg") -> Layout:
    """Assign columns, compute column widths, and fold into bands."""
    for i, op in enumerate(draw.ops):
        op.index = i
    spans = _assign_columns(draw)
    n_cols = max((op.col + 1 for op in draw.ops), default=0)
    widths = _column_widths(draw, geom, param_mode)
    while len(widths) < n_cols:
        widths.append(geom.min_col)
    fold_n = resolve_fold(fold, mode, n_cols)
    if fold_n <= 0 or n_cols <= fold_n:
        bands = [(0, n_cols - 1)] if n_cols else []
    else:
        bands = []
        start = 0
        while start < n_cols:
            end = min(start + fold_n, n_cols) - 1
            bands.append((start, end))
            start = end + 1
    return Layout(ops=draw.ops, n_cols=n_cols, col_widths=widths, spans=spans, bands=bands)
