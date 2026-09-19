"""Label text and semantic classification for circuit rendering."""

from __future__ import annotations

import math
from typing import Any

from .model import FLOW_OPS, DrawOp, display_param

__all__ = [
    "classify",
    "display_name",
    "param_strings",
    "label_lines",
    "tooltip",
    "cop_label",
    "to_pi",
    "fmt_num",
]

_PI_DENOMINATORS = (1, 2, 3, 4, 6, 8, 12, 24)


def fmt_num(x: Any) -> str:
    """Compact decimal rendering of a numeric parameter."""
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return str(x)
    if not math.isfinite(x):
        return str(x)
    if abs(x) >= 1000:
        return str(round(x))
    rounded = round(x * 1000) / 1000
    return str(int(rounded)) if rounded == int(rounded) else str(rounded)


def to_pi(x: Any) -> str | None:
    """Return a ``pi``-fraction string for *x* (e.g. ``π/2``), or None."""
    if not isinstance(x, (int, float)) or not math.isfinite(x):
        return None
    k = x / math.pi
    for d in _PI_DENOMINATORS:
        n = k * d
        if abs(n - round(n)) < 1e-6 and 0 < abs(round(n)) <= 24:
            num, den = round(n), d
            g = math.gcd(abs(num), den)
            num, den = num // g, den // g
            if den == 1:
                return "π" if num == 1 else ("-π" if num == -1 else f"{num}π")
            if num == 1:
                return f"π/{den}"
            if num == -1:
                return f"-π/{den}"
            return f"{num}π/{den}"
    return None


def param_strings(op: DrawOp, mode: str = "pi", *, greek: bool = True) -> list[str]:
    """Parameter display strings honoring *mode* (pi/decimal/symbol/hidden)."""
    if mode == "hidden" or not op.params:
        return []
    out = []
    for p in op.params:
        p = display_param(p, greek=greek)
        if isinstance(p, (int, float)):
            if mode == "pi":
                s = to_pi(p)
                if s is not None:
                    out.append(s)
                    continue
            out.append(fmt_num(p))
        else:
            out.append(str(p))
    return out


def display_name(op: DrawOp) -> str:
    """Display name for the operation (channels/QRAM/DEF carry their own)."""
    if op.op == "CHANNEL":
        return (op.name or "") + ("†" if op.dagger else "")
    if op.op == "QRAM":
        return "QRAM"
    if op.op == "DEF":
        return f"DEF {op.name}"
    return op.op + ("†" if op.dagger else "")


def label_lines(op: DrawOp, param_mode: str = "pi") -> tuple[str, str]:
    """Return ``(name_line, params_line)`` for a gate box."""
    ps = param_strings(op, param_mode)
    params = ",".join(ps)
    if len(ps) > 6:
        params = f"{len(ps)}p"
    return display_name(op), params


def cop_label(op: DrawOp) -> str:
    """Text for a classical instruction box, e.g. ``XOR c0←c1,c2``."""
    dest, srcs = op.cbits[0], op.cbits[1:]
    if op.name in ("NOT", "MOV"):
        return f"{op.name} c{dest}←c{srcs[0]}"
    return f"{op.name} c{dest}←c{srcs[0]},c{srcs[1]}"


def classify(op: DrawOp) -> str:
    """Semantic drawing kind for an operation.

    Returns one of: measure, reset, barrier, channel, qram, def, flow, cop,
    cx, cz, ccx, cswap, swap, mcx, cbox, span, box1.
    """
    ctrl = op.controls
    upper = op.op.upper()
    if op.op == "MEASURE":
        return "measure"
    if op.op == "RESET":
        return "reset"
    if op.op == "BARRIER":
        return "barrier"
    if op.op == "CHANNEL":
        return "channel"
    if op.op == "QRAM":
        return "qram"
    if op.op == "DEF":
        return "def"
    if op.op in FLOW_OPS:
        return "flow"
    if op.op == "COP":
        return "cop"
    if upper in ("CNOT", "CX") and not ctrl:
        return "cx"
    if upper in ("CZ", "CP", "CU1", "P") and not ctrl:
        return "cz"
    if upper in ("TOFFOLI", "CCX", "CCNOT") and not ctrl:
        return "ccx"
    if upper in ("CSWAP", "FREDKIN") and not ctrl:
        return "cswap"
    if upper == "SWAP" and not ctrl:
        return "swap"
    if upper == "X" and ctrl:
        return "mcx"
    if ctrl:
        return "cbox"
    if len(op.qubits) > 1:
        return "span"
    return "box1"


def tooltip(op: DrawOp) -> str:
    """One-line hover tooltip for an operation."""
    parts = [display_name(op) if op.op in ("CHANNEL", "DEF") else op.op + ("†" if op.dagger else "")]
    if op.qubits:
        parts.append("q[" + "],q[".join(str(q) for q in op.qubits) + "]")
    if op.cbits:
        parts.append("c[" + "],c[".join(str(c) for c in op.cbits) + "]")
    if op.params:
        flat = ", ".join(str(display_param(p)) for p in op.params)
        parts.append(f"({len(op.params)} params)" if len(op.params) > 6 else f"({flat})")
    if op.controls:
        parts.append("controlled_by q[" + "],q[".join(str(q) for q in op.controls) + "]")
    if op.cond:
        parts.append(f"cond: {op.cond}")
    if op.note:
        parts.append(op.note)
    return " · ".join(parts)
