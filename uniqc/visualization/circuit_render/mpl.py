"""matplotlib backend: draws the shared primitives onto a Figure.

Covers the ``mpl`` mode directly and serves as the PNG fallback when
``cairosvg`` is not installed.  matplotlib is imported lazily so the module
stays import-free until the mode is actually requested.
"""

from __future__ import annotations

from .model import DrawCircuit
from .options import RenderOptions
from .svg import build_primitives

__all__ = ["render_mpl", "render_png_bytes"]


def _draw_primitives(prims, width, height, opts: RenderOptions, theme_bg: str):

    import matplotlib

    matplotlib.use("Agg", force=True)
    from matplotlib import patches
    from matplotlib import pyplot as plt

    sc = (opts.scale or 100) / 100
    fig_w = max(2.0, width * sc / 96)
    fig_h = max(1.5, height * sc / 96)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=96)
    fig.patch.set_facecolor(theme_bg)
    ax.set_facecolor(theme_bg)
    ax.set_xlim(0, width * sc)
    ax.set_ylim(height * sc, 0)  # y down, matching SVG coordinates
    ax.axis("off")

    def mx(x):
        return x * sc

    def my(y):
        return y * sc

    for p in prims:
        t = p["t"]
        if t in ("g", "/g"):
            continue
        if t == "line":
            ax.plot(
                [mx(p["x1"]), mx(p["x2"])],
                [my(p["y1"]), my(p["y2"])],
                color=p.get("stroke", "#000"),
                linewidth=p.get("stroke-width", 1.2),
                linestyle=(0, tuple(int(v) for v in p["stroke-dasharray"].split()))
                if p.get("stroke-dasharray")
                else "-",
                solid_capstyle="round",
                zorder=2,
            )
        elif t == "rect":
            fill = p.get("fill", "none")
            hatch = "///" if fill.startswith("url(") else None
            face = "#ffffff" if hatch else fill
            if p.get("opacity") is not None and float(p["opacity"]) < 1:
                face = fill
            ax.add_patch(
                patches.Rectangle(
                    (mx(p["x"]), my(p["y"])),
                    p["w"] * sc,
                    p["h"] * sc,
                    facecolor=face,
                    edgecolor=p.get("stroke", "none"),
                    linewidth=p.get("stroke-width", 1.2),
                    hatch=hatch,
                    zorder=3,
                )
            )
        elif t == "circle":
            ax.add_patch(
                patches.Circle(
                    (mx(p["cx"]), my(p["cy"])),
                    p["r"] * sc,
                    facecolor=(p.get("fill") or "none"),
                    edgecolor=p.get("stroke", "none"),
                    linewidth=p.get("stroke-width", 1.2),
                    zorder=4,
                )
            )
        elif t == "text":
            ax.text(
                mx(p["x"]),
                my(p["y"]),
                p["txt"],
                fontsize=p.get("fs", 12) * sc,
                color=p.get("fill", "#000"),
                ha={"start": "left", "middle": "center", "end": "right"}.get(p.get("anchor", "middle"), "center"),
                va="center" if p.get("dominant-baseline") == "central" else "baseline",
                zorder=5,
            )
        elif t == "tri":
            ax.add_patch(
                patches.Polygon(
                    [(mx(a), my(b)) for a, b in p["pts"]],
                    closed=True,
                    facecolor=p.get("fill", "#000"),
                    edgecolor=p.get("stroke", "none"),
                    zorder=4,
                )
            )
        elif t == "arc":
            ax.add_patch(
                patches.Arc(
                    (mx(p["cx"]), my(p["cy"])),
                    2 * p["r"] * sc,
                    2 * p["r"] * sc,
                    theta1=p["a1"],
                    theta2=p["a2"],
                    color=p.get("stroke", "#000"),
                    linewidth=p.get("stroke-width", 1.2),
                    zorder=4,
                )
            )
    return fig


def render_mpl(draw: DrawCircuit, opts: RenderOptions):
    """Render to a matplotlib Figure (requires the ``[visualization]`` extra)."""
    if opts.vertical:
        raise ValueError("mpl mode does not support orientation='v'; use mode='svg'.")
    prims, width, height, meta, st = build_primitives(draw, opts)
    th = st.theme(opts.theme)
    return _draw_primitives(prims, width, height, opts, th.bg)


def render_png_bytes(draw: DrawCircuit, opts: RenderOptions) -> bytes:
    """Render to PNG bytes.

    Prefers ``cairosvg`` (exact SVG rasterization); falls back to the
    matplotlib primitive plotter when cairosvg is not installed.
    """
    if not opts.vertical:
        try:
            import cairosvg
        except ImportError:
            cairosvg = None
        if cairosvg is not None:
            from .svg import render_svg

            svg, _ = render_svg(draw, opts)
            return cairosvg.svg2png(bytestring=svg.encode("utf-8"))
    fig = render_mpl(draw, opts)
    import io

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    # Close the internal figure: png mode must not leak a pyplot figure
    # (docs runner captures all open figures; a leaked one shows up as junk).
    from matplotlib import pyplot as plt

    plt.close(fig)
    return buf.getvalue()
