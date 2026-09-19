"""Self-developed ASCII/Unicode text circuit renderer.

Replaces the old pyqpanda3-delegated text drawing (which is unavailable on
Python 3.14 and cannot express OriginIR-ext constructs).  All symbols are
anchored to the column center so control dots, targets and connectors align
exactly across rows.
"""

from __future__ import annotations

from .labels import classify, cop_label, display_name, param_strings
from .layout import layout_circuit, resolve_fold
from .model import FLOW_OPS, DrawCircuit, DrawOp
from .options import RenderOptions

__all__ = ["render_text"]

_UNI = {
    "H": "─",
    "V": "│",
    "CTL": "●",
    "TGT": "⊕",
    "SWP": "×",
    "QW": "═",
    "QV": "║",
    "BAR": "┊",
    "LB": "┤",
    "RB": "├",
    "CROSS": "╪",
    "RESET": "|0⟩",
}
_ASCII = {
    "H": "-",
    "V": "|",
    "CTL": "*",
    "TGT": "(+)",
    "SWP": "x",
    "QW": "=",
    "QV": "||",
    "BAR": ":",
    "LB": "|",
    "RB": "|",
    "CROSS": "#",
    "RESET": "|0>",
}


def _max_label(op: DrawOp, param_mode: str, sym) -> int:
    if op.op == "MEASURE":
        return 3
    if op.op == "BARRIER":
        return 1
    if op.op in FLOW_OPS:
        return 1
    if op.op == "COP":
        return len(cop_label(op)) + 4
    if op.op.upper() in ("CNOT", "CX", "CZ", "CP", "CU1", "P", "SWAP", "TOFFOLI", "CCX", "CSWAP") and not op.controls:
        return 5
    name = display_name(op)
    ps = param_strings(op, param_mode)
    pl = f"({len(ps)}p)" if len(ps) > 6 else (f"({','.join(ps)})" if ps else "")
    if op.op == "QRAM":
        return len(f"QRAM:{op.name}") + 4
    if op.op == "DEF":
        return len(f"DEF {op.name}{{..}}") + 4
    if op.op == "CHANNEL":
        name = "~" + (name[:4] + "." if len(name) > 10 else name)
    return len(name + pl) + 4


def _cell_label(op: DrawOp, kind: str, param_mode: str, uni: bool) -> str:
    if kind == "reset":
        return _UNI["RESET"] if uni else _ASCII["RESET"]
    if op.op == "QRAM":
        return f"QRAM:{op.name}"
    if op.op == "DEF":
        return f"DEF {op.name}" + "{…}" if uni else f"DEF {op.name}" + "{..}"
    if op.op == "CHANNEL":
        nm = op.name or ""
        nm = nm[:4] + "." if len(nm) > 10 else nm
        ps = param_strings(op, param_mode)
        pl = f"{len(ps)}p" if len(ps) > 6 else ",".join(ps)
        return "~" + nm + (f"({pl})" if pl else "")
    name = display_name(op)
    ps = param_strings(op, param_mode)
    return name + (f"({','.join(ps)})" if ps else "")


def render_text(draw: DrawCircuit, opts: RenderOptions) -> str:
    """Render a circuit as aligned ASCII/Unicode art."""
    uni = opts.charset == "unicode"
    S = _UNI if uni else _ASCII

    def asc_of(t: str) -> str:
        if uni:
            return t
        from .model import display_param_ascii

        return display_param_ascii(t)

    # The layout engine works in px-like units; for text we recompute widths in
    # character cells, so we only reuse column assignment + spans + bands.
    lay = layout_circuit(draw, _TextGeom(), "hidden", 0, mode="text")
    n_q = draw.n_qubits
    # Decision ⑨: classical wires hidden by default; auto-enable when the
    # circuit contains classical instructions that live on cbit lanes.
    need_clanes = opts.show_clbits or any(op.op == "COP" for op in draw.ops)
    n_c = draw.n_cbits if need_clanes else 0
    fold_n = resolve_fold(opts.fold, "text", lay.n_cols)
    bands = (
        [(0, lay.n_cols - 1)]
        if fold_n <= 0 or lay.n_cols <= fold_n
        else [(s, min(s + fold_n, lay.n_cols) - 1) for s in range(0, lay.n_cols, fold_n)]
    )
    out: list[str] = []

    for bi, (c_start, c_end) in enumerate(bands):
        if len(bands) > 1:
            out.append(("── " if uni else "-- ") + f"part {bi + 1}/{len(bands)} " + (S["H"] * 24))
        cols = list(range(c_start, c_end + 1))
        if not cols:
            continue
        width = dict.fromkeys(cols, 3)
        for op in lay.ops:
            if c_start <= op.col <= c_end:
                width[op.col] = max(width[op.col], _max_label(op, opts.param_mode, S))
        col_start, acc = {}, 0
        for c in cols:
            col_start[c] = acc
            acc += width[c] + 1

        rows = [("q", q) for q in range(n_q)]
        if n_c:
            rows.append(("sep", -1))
            rows += [("c", c) for c in range(n_c)]
        row_idx = {f"{k}{'' if i < 0 else i}": ri for ri, (k, i) in enumerate(rows)}
        grid = [[[] for _ in cols] for _ in rows]

        def put(ri, c, _grid=grid, _cols=cols, _cs=col_start, _rows=rows, **item):
            if 0 <= ri < len(_rows) and c in _cs:
                _grid[ri][_cols.index(c)].append(item)

        for op in lay.ops:
            if not (c_start <= op.col <= c_end):
                continue
            c, kind = op.col, classify(op)

            def ri(q, _idx=row_idx):
                return _idx[f"q{q}"]

            if kind in ("box1", "span", "reset", "channel", "qram", "def"):
                label = asc_of(_cell_label(op, kind, opts.param_mode, uni))
                # ascii 下 |0> 自带竖线，不再加盒界符，避免 ||0>| 的观感
                boxed = not (kind == "reset" and not uni)
                for k, q in enumerate(op.qubits):
                    put(ri(q), c, label=label if k == 0 else "", box=boxed)
            elif kind == "measure":
                put(ri(op.qubits[0]), c, label="M", box=True)
                cj = op.cbits[0] if op.cbits else None
                if cj is not None and f"c{cj}" in row_idx:
                    for r2 in range(ri(op.qubits[0]) + 1, row_idx[f"c{cj}"] + 1):
                        put(r2, c, vert="drop")
                    put(row_idx[f"c{cj}"], c, label=S["CROSS"], clane_mark=True)
            elif kind == "barrier":
                rws = [ri(q) for q in op.qubits]
                for r2 in range(min(rws), max(rws) + 1):
                    put(r2, c, bar=True)
            elif kind == "flow":
                pass  # brackets are emitted after the rows
            elif kind == "cop":
                put(row_idx[f"c{op.cbits[0]}"], c, label=asc_of(cop_label(op)), box=True, clane=True)
            else:
                ys_all = [ri(q) for q in op.qubits] + [ri(q) for q in op.controls]
                for r2 in range(min(ys_all), max(ys_all) + 1):
                    put(r2, c, vert="conn")
                for q in op.controls:
                    put(ri(q), c, label=S["CTL"])
                if kind == "cx":
                    put(ri(op.qubits[0]), c, label=S["CTL"])
                    put(ri(op.qubits[1]), c, label=S["TGT"])
                elif kind == "mcx":
                    put(ri(op.qubits[0]), c, label=S["TGT"])
                elif kind == "ccx":
                    put(ri(op.qubits[0]), c, label=S["CTL"])
                    put(ri(op.qubits[1]), c, label=S["CTL"])
                    put(ri(op.qubits[2]), c, label=S["TGT"])
                elif kind == "cz":
                    put(ri(op.qubits[0]), c, label=S["CTL"])
                    put(ri(op.qubits[1]), c, label=S["CTL"])
                elif kind == "swap":
                    put(ri(op.qubits[0]), c, label=S["SWP"])
                    put(ri(op.qubits[1]), c, label=S["SWP"])
                elif kind == "cswap":
                    put(ri(op.qubits[0]), c, label=S["CTL"])
                    put(ri(op.qubits[1]), c, label=S["SWP"])
                    put(ri(op.qubits[2]), c, label=S["SWP"])
                elif kind == "cbox":
                    for k, q in enumerate(op.qubits):
                        put(
                            ri(q),
                            c,
                            label=asc_of(_cell_label(op, kind, opts.param_mode, uni)) if k == 0 else "",
                            box=True,
                        )

        band_start_idx = len(out)
        for r_kind, r_i in rows:
            head = f"q[{r_i}] " if r_kind == "q" else (f"c[{r_i}] " if r_kind == "c" else "     ")
            line = head
            for ci, c in enumerate(cols):
                w = width[c]
                fill = S["H"] if r_kind == "q" else (S["QW"] if r_kind == "c" else " ")
                cell = fill * w
                ctr = w // 2
                ov = grid[rows.index((r_kind, r_i))][ci]
                # two passes: connectors/barriers first, then labels (labels win)
                for item in [it for it in ov if it.get("vert") or it.get("bar")]:
                    if item.get("vert"):
                        v = S["QV"] if item["vert"] == "drop" else S["V"]
                        cell = cell[:ctr] + v + cell[ctr + len(v) :]
                    elif item.get("bar"):
                        cell = cell[:ctr] + S["BAR"] + cell[ctr + 1 :]
                for item in [it for it in ov if not (it.get("vert") or it.get("bar"))]:
                    label = item.get("label")
                    if label:
                        txt = (S["LB"] + label + S["RB"]) if (item.get("box") or item.get("clane_mark")) else label
                        pos = max(0, ctr - len(txt) // 2)
                        cell = cell[:pos] + txt + cell[pos + len(txt) :]
                    elif item.get("box"):
                        cell = S["LB"] + fill * (w - 2) + S["RB"]
                line += cell + (fill if ci < len(cols) - 1 else "")
            out.append(line.rstrip())

        for sp in lay.spans:
            c1, c2 = max(sp.col_begin, c_start), min(sp.col_end, c_end)
            if c1 > c2:
                continue
            lbl = f" {sp.kind} {sp.cond} "
            x1, x2 = col_start[c1] + 1, col_start[c2] + width[c2] - 1
            if x2 - x1 < len(lbl) + 2:
                x2 = x1 + len(lbl) + 2
            span = x2 - x1 - len(lbl)
            dash_l, dash_r = max(1, span // 2), max(1, span - span // 2)
            bracket = "└" + S["H"] * dash_l + lbl + S["H"] * dash_r + "┘"
            out.insert(band_start_idx, "     " + " " * x1 + bracket)

    return "\n".join(out)


class _TextGeom:
    """Minimal geometry shim so text mode can reuse the column assigner."""

    fs = 10.0
    pfs = 10.0
    min_col = 1.0
    pad = 0.0
