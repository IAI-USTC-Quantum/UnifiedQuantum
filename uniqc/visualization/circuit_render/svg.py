"""SVG primitives and the main graphical renderer.

The drawing pipeline is two-stage: :func:`build_primitives` emits
style-agnostic geometric primitives in *logical* coordinates (x = time axis,
y = wire axis); :func:`serialize_svg` maps them to SVG text, handling the
optional vertical orientation (transpose) and scale.  Keeping these separate
is what lets the matplotlib backend (mpl/png) reuse the exact same drawing.
"""

from __future__ import annotations

import html as _html
import math

from .labels import classify, cop_label, label_lines, param_strings, tooltip
from .layout import estimate_text_width, layout_circuit
from .model import FLOW_OPS, DrawCircuit, DrawOp
from .options import RenderOptions
from .styles import Style, get_style

__all__ = ["build_primitives", "serialize_svg", "render_svg", "RenderMeta"]

# ---------------------------------------------------------------------------
# Primitive constructors (plain dicts; coordinates are logical)
# ---------------------------------------------------------------------------


def _line(x1, y1, x2, y2, **kw):
    return {"t": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2, **kw}


def _rect(x, y, w, h, **kw):
    return {"t": "rect", "x": x, "y": y, "w": w, "h": h, **kw}


def _circ(cx, cy, r, **kw):
    return {"t": "circle", "cx": cx, "cy": cy, "r": r, **kw}


def _text(x, y, txt, **kw):
    return {"t": "text", "x": x, "y": y, "txt": str(txt), **kw}


def _tri(pts, **kw):
    return {"t": "tri", "pts": pts, **kw}


def _arc(cx, cy, r, a1, a2, **kw):
    return {"t": "arc", "cx": cx, "cy": cy, "r": r, "a1": a1, "a2": a2, **kw}


def _gbegin(**kw):
    return {"t": "g", **kw}


_GEND = {"t": "/g"}


class RenderMeta(dict):
    """Render statistics (column count, band count, style)."""


# ---------------------------------------------------------------------------
# Semantic op drawing
# ---------------------------------------------------------------------------


def _ctrl_dot(pr, x, y, st, th):
    pr.append(_circ(x, y, st.ctrl_r, fill=th.ink))


def _target_circ(pr, x, y, st, th):
    r = st.targ_r
    pr.append(_circ(x, y, r, fill="none", stroke=th.ink, **{"stroke-width": st.sw + 0.2}))
    pr.append(_line(x - r - 3, y, x + r + 3, y, stroke=th.ink, **{"stroke-width": st.sw + 0.2}))
    pr.append(_line(x, y - r - 3, x, y + r + 3, stroke=th.ink, **{"stroke-width": st.sw + 0.2}))


def _swap_cross(pr, x, y, st, th, s=6.0):
    pr.append(_line(x - s, y - s, x + s, y + s, stroke=th.ink, **{"stroke-width": st.sw + 0.3}))
    pr.append(_line(x - s, y + s, x + s, y - s, stroke=th.ink, **{"stroke-width": st.sw + 0.3}))


def _connector(pr, x, ys, st, th):
    pr.append(_line(x, min(ys), x, max(ys), stroke=th.ink, **{"stroke-width": st.sw + 0.1}))


def _family(op: DrawOp) -> str:
    if op.op == "CHANNEL":
        return "channel"
    if op.op == "QRAM":
        return "qram"
    if op.op == "DEF":
        return "def"
    if op.op == "COP":
        return "cop"
    if op.op == "MEASURE":
        return "measure"
    if op.op == "RESET":
        return "reset"
    if op.op == "BARRIER" or op.op in FLOW_OPS:
        return "meta"
    if op.params:
        return "grot"
    if len(op.qubits) > 1 or op.controls:
        return "g2"
    return "g1"


def _draw_gate_box(pr, cx, cy_top, cy_bot, op, st: Style, th, opts: RenderOptions, *, fam=None, hatch_id=""):
    name, params = label_lines(op, opts.param_mode)
    look = st.look(th, fam or _family(op))
    w = (
        max(
            estimate_text_width(name, st.fs),
            estimate_text_width(params, st.pfs) if params else 0.0,
        )
        + st.pad
    )
    x0 = cx - w / 2
    fill = look.fill
    if fill == "hatch":
        fill = f"url(#{hatch_id})"
    single = cy_bot == cy_top
    text_h = (st.fs + st.pfs + 6) if params else (st.fs + 8)
    half_h = max(st.box_h / 2, text_h / 2 + 4)
    y0 = cy_top - half_h if single else min(cy_top - st.box_h * 0.5, (cy_top + cy_bot) / 2 - text_h / 2 - 4)
    y1 = cy_top + half_h if single else max(cy_bot + st.box_h * 0.5, (cy_top + cy_bot) / 2 + text_h / 2 + 4)
    pr.append(
        _rect(x0, y0, w, y1 - y0, fill=fill, stroke=look.stroke, rx=st.rx, **{"stroke-width": st.sw, "class": "gbox"})
    )
    yc = cy_top if single else (cy_top + cy_bot) / 2
    ny = yc - st.fs * 0.42 if params else yc
    pr.append(
        _text(
            cx,
            ny,
            name,
            fs=st.fs,
            fill=look.ink,
            **{"font-family": st.font, "dominant-baseline": "central", "class": "gtext"},
        )
    )
    if params:
        pr.append(
            _text(
                cx,
                yc + st.pfs * 0.9,
                params,
                fs=st.pfs,
                fill=look.ink,
                opacity=0.92,
                **{"font-family": st.font, "dominant-baseline": "central", "class": "gtext"},
            )
        )


def _draw_op(pr, op: DrawOp, x, geom, st: Style, th, opts: RenderOptions):
    yq, yc = geom["yq"], geom["yc"]
    kind = classify(op)
    pr.append(_gbegin(**{"class": "op", "data-i": op.index, "tip": tooltip(op)}))
    ys = [yq(q) for q in op.qubits]
    y_all = ys + [yq(q) for q in op.controls]
    if kind in ("box1", "span"):
        if ys:
            _draw_gate_box(pr, x, min(ys), max(ys), op, st, th, opts, hatch_id=geom["hatch_id"])
    elif kind in ("cx", "mcx"):
        ctrls = [op.qubits[0]] if kind == "cx" else list(op.controls)
        targ = op.qubits[1] if kind == "cx" else op.qubits[0]
        _connector(pr, x, [yq(targ)] + [yq(q) for q in ctrls], st, th)
        for q in ctrls:
            _ctrl_dot(pr, x, yq(q), st, th)
        _target_circ(pr, x, yq(targ), st, th)
    elif kind == "ccx":
        _connector(pr, x, ys, st, th)
        _ctrl_dot(pr, x, yq(op.qubits[0]), st, th)
        _ctrl_dot(pr, x, yq(op.qubits[1]), st, th)
        _target_circ(pr, x, yq(op.qubits[2]), st, th)
    elif kind == "cz":
        _connector(pr, x, ys, st, th)
        _ctrl_dot(pr, x, yq(op.qubits[0]), st, th)
        _ctrl_dot(pr, x, yq(op.qubits[1]), st, th)
        ps = param_strings(op, opts.param_mode)
        if ps:
            pr.append(_text(x, min(ys) - 8, ",".join(ps), fs=st.pfs, fill=th.dim, **{"font-family": st.font}))
    elif kind == "cswap":
        _connector(pr, x, ys, st, th)
        _ctrl_dot(pr, x, yq(op.qubits[0]), st, th)
        _swap_cross(pr, x, yq(op.qubits[1]), st, th)
        _swap_cross(pr, x, yq(op.qubits[2]), st, th)
    elif kind == "swap":
        _connector(pr, x, ys, st, th)
        _swap_cross(pr, x, yq(op.qubits[0]), st, th)
        _swap_cross(pr, x, yq(op.qubits[1]), st, th)
    elif kind == "cbox":
        _connector(pr, x, y_all, st, th)
        for q in op.controls:
            _ctrl_dot(pr, x, yq(q), st, th)
        _draw_gate_box(pr, x, min(ys), max(ys), op, st, th, opts, hatch_id=geom["hatch_id"])
    elif kind == "measure":
        y = yq(op.qubits[0])
        look = st.look(th, "measure")
        bw, bh = max(30.0, st.box_h * 0.9), st.box_h
        pr.append(
            _rect(
                x - bw / 2,
                y - bh / 2,
                bw,
                bh,
                fill=look.fill,
                stroke=look.stroke,
                rx=st.rx,
                **{"stroke-width": st.sw, "class": "gbox"},
            )
        )
        gy, gr = y + bh * 0.22, bh * 0.26
        pr.append(_arc(x, gy, gr, 180, 360, stroke=look.ink, fill="none", **{"stroke-width": st.sw}))
        pr.append(_line(x - gr - 3, gy, x + gr + 3, gy, stroke=look.ink, **{"stroke-width": st.sw * 0.8}))
        na = -52 * 3.141592653589793 / 180
        pr.append(
            _line(
                x,
                gy,
                x + gr * 0.92 * math.cos(na),
                gy + gr * 0.92 * math.sin(na),
                stroke=look.ink,
                **{"stroke-width": st.sw},
            )
        )
        cj = op.cbits[0] if op.cbits else None
        if opts.show_clbits and cj is not None and geom["c_exists"](cj):
            ycj = yc(cj)
            pr.append(
                _line(x, y + bh / 2, x, ycj - 10, stroke=th.dim, **{"stroke-width": 1.2, "stroke-dasharray": "4 3"})
            )
            pr.append(_tri([(x - 3.5, ycj - 10), (x + 3.5, ycj - 10), (x, ycj - 4)], fill=th.dim))
    elif kind == "reset":
        _draw_gate_box(
            pr, x, yq(op.qubits[0]), yq(op.qubits[0]), DrawOp(op="|0⟩", qubits=op.qubits), st, th, opts, fam="reset"
        )
    elif kind == "barrier":
        mn, mx = min(ys) - 13, max(ys) + 13
        pr.append(_line(x, mn, x, mx, stroke=th.dim, **{"stroke-width": 2, "stroke-dasharray": "6 4"}))
        for y in ys:
            pr.append(_rect(x - 2.6, y - 2.6, 5.2, 5.2, fill=th.dim))
    elif kind == "channel":
        _draw_gate_box(pr, x, min(ys), max(ys), op, st, th, opts, fam="channel", hatch_id=geom["hatch_id"])
    elif kind == "qram":
        y_top, y_bot = min(ys) - 14, max(ys) + 14
        w = max(74.0, estimate_text_width(f"QRAM {op.name}", st.fs) + 20)
        x0 = x - w / 2
        look = st.look(th, "qram")
        fill = look.fill if look.fill != "hatch" else f"url(#{geom['hatch_id']})"
        pr.append(
            _rect(
                x0,
                y_top,
                w,
                y_bot - y_top,
                fill=fill,
                stroke=look.stroke,
                rx=st.rx or 3,
                **{"stroke-width": st.sw + 0.3, "class": "gbox"},
            )
        )
        n_addr = op.addr or len(op.qubits) // 2
        y_div = (yq(op.qubits[n_addr - 1]) + yq(op.qubits[n_addr])) / 2
        pr.append(
            _line(x0, y_div, x0 + w, y_div, stroke=look.stroke, **{"stroke-width": 1.1, "stroke-dasharray": "4 3"})
        )
        y_mid = (y_top + y_bot) / 2
        pr.append(
            _text(
                x,
                y_mid - 8,
                "QRAM",
                fs=st.fs,
                fill=look.ink,
                **{"font-family": st.font, "dominant-baseline": "central"},
            )
        )
        pr.append(
            _text(
                x,
                y_mid + 9,
                op.name or "",
                fs=st.pfs,
                fill=look.ink,
                opacity=0.85,
                **{"font-family": st.font, "dominant-baseline": "central"},
            )
        )
        pr.append(
            _text(
                x0 + 5,
                yq(op.qubits[0]),
                "addr",
                fs=8.5,
                fill=th.dim,
                anchor="start",
                **{"font-family": st.font, "dominant-baseline": "central"},
            )
        )
        pr.append(
            _text(
                x0 + 5,
                yq(op.qubits[-1]),
                "data",
                fs=8.5,
                fill=th.dim,
                anchor="start",
                **{"font-family": st.font, "dominant-baseline": "central"},
            )
        )
    elif kind == "def":
        y_mid0 = (min(ys) + max(ys)) / 2
        y_top, y_bot = min(min(ys) - 16, y_mid0 - 26), max(max(ys) + 16, y_mid0 + 26)
        w = max(62.0, estimate_text_width(f"DEF {op.name}", st.fs) + 22)
        x0 = x - w / 2
        look = st.look(th, "def")
        pr.append(
            _rect(
                x0,
                y_top,
                w,
                y_bot - y_top,
                fill=look.fill,
                stroke=look.stroke,
                rx=st.rx or 2,
                **{"stroke-width": st.sw, "class": "gbox"},
            )
        )
        pr.append(
            _rect(
                x0 + 3,
                y_top + 3,
                w - 6,
                y_bot - y_top - 6,
                fill="none",
                stroke=look.stroke,
                rx=max(0, (st.rx or 2) - 2),
                **{"stroke-width": 0.9},
            )
        )
        y_mid = (y_top + y_bot) / 2
        pr.append(
            _text(
                x,
                y_mid - 6,
                f"DEF {op.name}",
                fs=st.fs,
                fill=look.ink,
                **{"font-family": st.font, "dominant-baseline": "central"},
            )
        )
        if op.note:
            pr.append(
                _text(
                    x,
                    y_mid + 9,
                    op.note,
                    fs=st.pfs - 1,
                    fill=th.dim,
                    **{"font-family": st.font, "dominant-baseline": "central"},
                )
            )
    elif kind == "cop":
        y = yc(op.cbits[0])
        lbl = cop_label(op)
        w = estimate_text_width(lbl, 11) + 16
        look = st.look(th, "cop")
        pr.append(
            _rect(
                x - w / 2,
                y - 13,
                w,
                26,
                fill=look.fill,
                stroke=look.stroke,
                rx=4,
                **{"stroke-width": 1.2, "class": "gbox"},
            )
        )
        pr.append(_text(x, y, lbl, fs=11, fill=th.ink, **{"font-family": st.font, "dominant-baseline": "central"}))
    # "flow" markers are drawn as brackets in build_primitives
    pr.append(_GEND)


# ---------------------------------------------------------------------------
# Primitive-level scene construction (shared by svg + mpl)
# ---------------------------------------------------------------------------


def build_primitives(draw: DrawCircuit, opts: RenderOptions) -> tuple[list, float, float, RenderMeta, Style]:
    """Lay out *draw* and emit drawing primitives; returns (prims, W, H, meta, style)."""
    st = get_style(opts.style)
    th = st.theme(opts.theme)
    layout = layout_circuit(draw, st, opts.param_mode, opts.fold, mode=opts.mode or "svg")
    # Decision ⑨: classical wires hidden by default; but a circuit with
    # classical instructions (COP) would lose content — auto-enable then.
    need_clanes = opts.show_clbits or any(op.op == "COP" for op in draw.ops)
    n_q, n_c = draw.n_qubits, draw.n_cbits if need_clanes else 0
    asc = opts.qubit_order != "desc"
    label_w, top = 54.0, 44.0
    hatch_id = f"hp{id(opts) & 0xFFFFFF:x}"

    def yq(i):
        return top + (i if asc else n_q - 1 - i) * st.wire_gap

    def yc(j):
        return top + n_q * st.wire_gap + 22 + j * 28

    geom = {"yq": yq, "yc": yc, "c_exists": lambda j: j < n_c, "hatch_id": hatch_id}

    prims: list[dict] = []
    width = 0.0
    for bi, (c_start, c_end) in enumerate(layout.bands):
        bx0 = 12 + label_w
        sum_w = sum(layout.col_widths[c_start : c_end + 1])
        band_w = bx0 + sum_w + 18
        width = max(width, band_w)

        def col_x(c, _s=c_start, _bx0=bx0):
            return _bx0 + sum(layout.col_widths[_s:c]) + layout.col_widths[c] / 2

        y_bot_q = top + (n_q - 1) * st.wire_gap
        band_h = (yc(n_c - 1) + 16) if n_c else (y_bot_q + 18)
        for q in range(n_q):
            y = yq(q)
            prims.append(
                _text(
                    10,
                    y,
                    f"q[{q}]",
                    fs=12,
                    fill=th.dim,
                    anchor="start",
                    **{"font-family": st.font, "dominant-baseline": "central"},
                )
            )
            prims.append(_line(bx0 - 10, y, band_w - 10, y, stroke=th.wire, **{"stroke-width": st.wire_w}))
        for c in range(n_c):
            y = yc(c)
            prims.append(
                _text(
                    10,
                    y,
                    f"c[{c}]",
                    fs=11,
                    fill=th.dim,
                    anchor="start",
                    **{"font-family": st.font, "dominant-baseline": "central"},
                )
            )
            prims.append(_line(bx0 - 10, y - 2.4, band_w - 10, y - 2.4, stroke=th.clane, **{"stroke-width": 1.2}))
            prims.append(_line(bx0 - 10, y + 2.4, band_w - 10, y + 2.4, stroke=th.clane, **{"stroke-width": 1.2}))
        if bi > 0:
            prims.append(
                _text(
                    bx0,
                    14,
                    f"↳ 续 {bi + 1}/{len(layout.bands)}（折叠自上一行末尾）",
                    fs=10.5,
                    fill=th.hint,
                    anchor="start",
                    **{"font-family": st.font},
                )
            )
        for sp in layout.spans:
            c1, c2 = max(sp.col_begin, c_start), min(sp.col_end, c_end)
            if c1 > c2:
                continue
            x1, x2, y_b = col_x(c1) - 6, col_x(c2) + 6, top - 16
            if opts.style == "modern":
                prims.append(_rect(x1, top - 8, x2 - x1, y_bot_q - top + 16, fill=th.bracket, opacity=0.05))
            prims.append(_line(x1, y_b, x2, y_b, stroke=th.bracket, **{"stroke-width": 1.4}))
            prims.append(_line(x1, y_b, x1, y_b + 6, stroke=th.bracket, **{"stroke-width": 1.4}))
            prims.append(_line(x2, y_b, x2, y_b + 6, stroke=th.bracket, **{"stroke-width": 1.4}))
            prims.append(
                _text(
                    (x1 + x2) / 2, y_b - 4, f"{sp.kind} {sp.cond}", fs=10.5, fill=th.bracket, **{"font-family": st.font}
                )
            )
        for op in layout.ops:
            if op.op == "QELSE" and c_start <= op.col <= c_end:
                prims.append(
                    _text(
                        col_x(op.col),
                        top - 2,
                        "else",
                        fs=9.5,
                        fill=th.dim,
                        **{"font-family": st.font, "font-style": "italic", "dominant-baseline": "central"},
                    )
                )
        for op in layout.ops:
            if c_start <= op.col <= c_end:
                _draw_op(prims, op, col_x(op.col), geom, st, th, opts)
        if bi < len(layout.bands) - 1:
            prims.append({"t": "_shift", "h": band_h + 34})

    shift = 0.0
    for p in prims:
        if p["t"] == "_shift":
            shift += p["h"]
            continue
        for k in ("y", "y1", "y2", "cy"):
            if k in p:
                p[k] += shift
        if "pts" in p:
            p["pts"] = [(a, b + shift) for a, b in p["pts"]]
    total_h = (yc(n_c - 1) + 16 if n_c else top + (n_q - 1) * st.wire_gap + 18) + shift + 6
    height = max(total_h, 60.0)
    meta = RenderMeta(style=opts.style, n_cols=layout.n_cols, bands=len(layout.bands), hatch_id=hatch_id)
    return [p for p in prims if p["t"] != "_shift"], width, height, meta, st


# ---------------------------------------------------------------------------
# SVG serialization
# ---------------------------------------------------------------------------

_ATTR_KEYS = ("fill", "stroke", "stroke-width", "stroke-dasharray", "stroke-linecap", "opacity", "class", "rx")


def _attrs(p: dict, keys) -> str:
    out = ""
    for k in keys:
        v = p.get(k)
        if v is None:
            continue
        if isinstance(v, float):
            v = round(v, 2)
        out += f' class="{v}"' if k == "class" else f' {k}="{_html.escape(str(v), quote=True)}"'
    return out


def serialize_svg(
    prims: list[dict], width: float, height: float, opts: RenderOptions, *, defs: str = "", css: str = ""
) -> str:
    """Serialize primitives to SVG text; transposes axes for vertical mode."""
    vert = opts.vertical
    sc = (opts.scale or 100) / 100
    vpad = 18 if vert else 0

    def mp(x, y):
        return (y * sc, x * sc + vpad) if vert else (x * sc, y * sc)

    def num(v):
        return round(v, 2)

    out_w = num((height if vert else width) * sc)
    out_h = num((width if vert else height) * sc + vpad)
    parts = [
        f'<svg class="uniqc-viz" xmlns="http://www.w3.org/2000/svg" width="{out_w}" height="{out_h}" '
        f'viewBox="0 0 {out_w} {out_h}" role="img">'
    ]
    if defs:
        parts.append(f"<defs>{defs}</defs>")
    if css:
        parts.append(f"<style>{css}</style>")
    for p in prims:
        t = p["t"]
        if t == "g":
            extra = f' data-i="{p["data-i"]}"' if p.get("data-i") is not None else ""
            parts.append(f'<g class="{p.get("class", "")}"{extra}>')
            if p.get("tip"):
                parts.append(f"<title>{_html.escape(str(p['tip']))}</title>")
        elif t == "/g":
            parts.append("</g>")
        elif t == "line":
            x1, y1 = mp(p["x1"], p["y1"])
            x2, y2 = mp(p["x2"], p["y2"])
            parts.append(f'<line x1="{num(x1)}" y1="{num(y1)}" x2="{num(x2)}" y2="{num(y2)}"{_attrs(p, _ATTR_KEYS)}/>')
        elif t == "rect":
            x, y = mp(p["x"], p["y"])
            w = (p["h"] if vert else p["w"]) * sc
            h = (p["w"] if vert else p["h"]) * sc
            parts.append(
                f'<rect x="{num(x)}" y="{num(y)}" width="{num(max(0, w))}" height="{num(max(0, h))}"{_attrs(p, _ATTR_KEYS)}/>'
            )
        elif t == "circle":
            cx, cy = mp(p["cx"], p["cy"])
            parts.append(f'<circle cx="{num(cx)}" cy="{num(cy)}" r="{num(p["r"] * sc)}"{_attrs(p, _ATTR_KEYS)}/>')
        elif t == "text":
            x, y = mp(p["x"], p["y"])
            rot = f' transform="rotate(-90,{num(x)},{num(y)})"' if vert else ""
            anchor = p.get("anchor", "middle")
            parts.append(
                f'<text x="{num(x)}" y="{num(y)}" font-size="{num(p.get("fs", 12) * sc)}"'
                f"{_attrs(p, ('fill', 'font-family', 'font-style', 'font-weight', 'opacity', 'class', 'dominant-baseline'))}"
                f' text-anchor="{anchor}"{rot}>{_html.escape(p["txt"])}</text>'
            )
        elif t == "tri":
            pts = " ".join(f"{num(a)},{num(b)}" for a, b in (mp(*pt) for pt in p["pts"]))
            parts.append(f'<polygon points="{pts}"{_attrs(p, _ATTR_KEYS)}/>')
        elif t == "arc":

            def pt(a, _p=p):
                return mp(
                    _p["cx"] + _p["r"] * math.cos(a * math.pi / 180), _p["cy"] + _p["r"] * math.sin(a * math.pi / 180)
                )

            (x1, y1), (x2, y2) = pt(p["a1"]), pt(p["a2"])
            r = p["r"] * sc
            large = 1 if abs(p["a2"] - p["a1"]) > 180 else 0
            sweep = 0 if vert else 1
            parts.append(
                f'<path d="M {num(x1)} {num(y1)} A {num(r)} {num(r)} 0 {large} {sweep} {num(x2)} {num(y2)}"'
                f"{_attrs(p, _ATTR_KEYS)}/>"
            )
    parts.append("</svg>")
    return "\n".join(parts)


def render_svg(draw: DrawCircuit, opts: RenderOptions) -> tuple[str, RenderMeta]:
    """Render a DrawCircuit to SVG text; returns (svg, meta)."""
    prims, width, height, meta, st = build_primitives(draw, opts)
    hatch_id = meta["hatch_id"]
    defs = (
        f'<pattern id="{hatch_id}" width="6" height="6" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">'
        '<line x1="0" y1="0" x2="0" y2="6" stroke="#888" stroke-width="1.1"/></pattern>'
    )
    css = (
        ".op{cursor:pointer}"
        ".op:hover .gbox{stroke-width:2.6}"
        + (".op:hover .gbox{filter:drop-shadow(0 0 4px rgba(99,102,241,.65))}" if opts.style == "modern" else "")
        + ".op:hover .gtext{font-weight:600}"
    )
    return serialize_svg(prims, width, height, opts, defs=defs, css=css), meta
