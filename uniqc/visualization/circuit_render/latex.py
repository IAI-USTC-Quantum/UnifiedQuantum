"""quantikz LaTeX export for circuit rendering.

Emits source for the ``quantikz`` package (tikzlibrary ``quantikz2``), the
de-facto standard for quantum-circuit figures in papers.  Constructs that
quantikz cannot express (classical instructions, QIF/QWHILE control flow,
channel semantics) degrade to comments plus placeholder gates — the output
always compiles.

Verified syntax (TeX Live quantikz2): ``\\gate[wires=N,style={...}]{...}``,
``\\ctrl{Δ}`` / ``\\targ{}`` / ``\\control{}``, ``\\swap{Δ}`` / ``\\targX{}``,
``\\meter{}``, ``\\slice{}`` for barriers.
"""

from __future__ import annotations

from .labels import classify, cop_label, to_pi
from .layout import layout_circuit
from .model import DrawCircuit
from .options import RenderOptions
from .styles import get_style

__all__ = ["render_latex"]

_TEX_SYM = {"α₂": r"\alpha_2", "θ": r"\theta", "φ": r"\phi", "π": r"\pi", "α": r"\alpha", "₂": "_2", "†": r"^\dag"}

_TEX_NAME = {
    "RX": "R_X",
    "RY": "R_Y",
    "RZ": "R_Z",
    "U1": "U_1",
    "U2": "U_2",
    "U3": "U_3",
    "RPhi": r"R_\Phi",
    "RPhi90": r"R_{\Phi 90}",
    "RPhi180": r"R_{\Phi 180}",
}


def _tex_params(op, mode: str) -> list[str]:
    """Raw params -> LaTeX strings (numbers become \\frac{\\pi}{2} when close)."""
    if mode == "hidden" or not op.params:
        return []
    from .labels import fmt_num
    from .model import display_param

    out = []
    for p in op.params:
        p = display_param(p)
        if isinstance(p, (int, float)):
            pi = to_pi(p) if mode == "pi" else None
            if pi is not None:
                import re

                m = re.match(r"^(-?)(\d*)π/(\d+)$", pi)
                if m:
                    out.append(f"{m.group(1)}\\frac{{{m.group(2)}\\pi}}{{{m.group(3)}}}")
                else:
                    out.append(pi.replace("π", r"\pi"))
            else:
                out.append(fmt_num(p))
        else:
            s = str(p)
            for src, dst in _TEX_SYM.items():
                s = s.replace(src, dst)
            out.append(s)
    return out


def _tex_name(op) -> str:
    base = _TEX_NAME.get(op.op, op.op)
    return base + (r"^{\dag}" if op.dagger else "")


def render_latex(draw: DrawCircuit, opts: RenderOptions) -> str:
    """Render a circuit as quantikz LaTeX source (compilable standalone block)."""
    st = get_style(opts.style)  # style affects geometry defaults only
    lay = layout_circuit(draw, st, "hidden", 0, mode="latex")
    n_q = draw.n_qubits
    comments: list[str] = []
    if draw.params:
        comments.append("% PARAM " + ", ".join(draw.params))
    grid = [[None] * lay.n_cols for _ in range(n_q)]
    skip = [[False] * lay.n_cols for _ in range(n_q)]

    def put(q, c, tok):
        if 0 <= q < n_q and 0 <= c < lay.n_cols:
            grid[q][c] = tok

    for op in lay.ops:
        c, kind = op.col, classify(op)
        qs = list(op.qubits)
        if kind == "box1":
            ps = _tex_params(op, opts.param_mode)
            inner = _tex_name(op) + (f"({','.join(ps)})" if ps else "")
            put(qs[0], c, rf"\gate{{{inner}}}")
        elif kind in ("span", "channel"):
            ps = _tex_params(op, opts.param_mode)
            nm = op.name if kind == "channel" else _tex_name(op)
            inner = nm + ("(" + (rf"\times {len(ps)}" if len(ps) > 6 else ",".join(ps)) + ")") if ps else nm
            n, q0 = len(qs), min(qs)
            style = ",style={dashed}" if kind == "channel" else ""
            put(q0, c, rf"\gate[wires={n}{style}]{{{inner}}}")
            for k in range(1, n):
                skip[qs[k]][c] = True
        elif kind in ("cx", "mcx"):
            ctrls = [qs[0]] if kind == "cx" else list(op.controls)
            targ = qs[1] if kind == "cx" else qs[0]
            for q in ctrls:
                put(q, c, rf"\ctrl{{{targ - q}}}")
            put(targ, c, r"\targ{}")
        elif kind == "ccx":
            put(qs[0], c, rf"\ctrl{{{qs[2] - qs[0]}}}")
            put(qs[1], c, rf"\ctrl{{{qs[2] - qs[1]}}}")
            put(qs[2], c, r"\targ{}")
        elif kind == "cz":
            put(qs[0], c, rf"\ctrl{{{qs[1] - qs[0]}}}")
            put(qs[1], c, r"\control{}")
            ps = _tex_params(op, opts.param_mode)
            if ps:
                comments.append(f"% {op.op} params: {', '.join(ps)} (controlled-phase angle)")
        elif kind == "swap":
            put(qs[0], c, rf"\swap{{{qs[1] - qs[0]}}}")
            put(qs[1], c, r"\targX{}")
        elif kind == "cswap":
            put(qs[0], c, rf"\ctrl{{{qs[1] - qs[0]}}}")
            put(qs[1], c, rf"\swap{{{qs[2] - qs[1]}}}")
            put(qs[2], c, r"\targX{}")
        elif kind == "cbox":
            ps = _tex_params(op, opts.param_mode)
            for q in op.controls:
                put(q, c, rf"\ctrl{{{qs[0] - q}}}")
            inner = _tex_name(op) + (f"({','.join(ps)})" if ps else "")
            put(qs[0], c, rf"\gate{{{inner}}}")
        elif kind == "measure":
            put(qs[0], c, r"\meter{}")
            cj = op.cbits[0] if op.cbits else None
            if cj is not None:
                comments.append(f"% MEASURE q[{qs[0]}] -> c[{cj}] (classical wire omitted in quantikz)")
        elif kind == "reset":
            put(qs[0], c, r"\gate{|0\rangle} % RESET")
        elif kind == "barrier":
            put(min(qs), c, r"\slice{}")
            comments.append(f"% BARRIER on q[{'],q['.join(map(str, qs))}] rendered as a full-height \\slice{{}}")
        elif kind == "qram":
            put(qs[0], c, rf"\gate[wires={len(qs)}]{{\text{{QRAM }}{op.name}}}")
            for k in range(1, len(qs)):
                skip[qs[k]][c] = True
            comments.append(
                f"% QRAM {op.name}: addr q[{'],q['.join(map(str, qs[: op.addr or 2]))}]"
                f" / data q[{'],q['.join(map(str, qs[op.addr or 2 :]))}]"
            )
        elif kind == "def":
            put(qs[0], c, rf"\gate[wires={len(qs)},style={{double}}]{{\text{{DEF: }}{op.name}}}")
            for k in range(1, len(qs)):
                skip[qs[k]][c] = True
        elif kind == "cop":
            comments.append(f"% classical: {cop_label(op)} (no classical op support in quantikz)")
        elif kind == "flow":
            comments.append(f"% {op.op} {op.cond or ''} (OriginIR-ext control flow; not expressible in quantikz)")

    lines = list(comments)
    lines.append(r"\begin{quantikz}[column sep=0.9em, row sep=0.5em]")
    for q in range(n_q):
        row = f"  q[{q}]"
        for c in range(lay.n_cols):
            if skip[q][c]:
                continue
            row += " & " + (grid[q][c] or r"\qw")
        row += r" \\"
        lines.append(row)
    lines.append(r"\end{quantikz}")
    return "\n".join(lines)
