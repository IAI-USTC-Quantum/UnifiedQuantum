"""Visual style definitions for circuit rendering.

Four skins over one semantic core (control dot / target circle, spanning
boxes for couplings, boxed gauge for measurement, double-line classical
wires).  ``quantikz`` is the default skin chosen in the design review.

A style is geometry + fonts + a per-family ``look`` (fill/stroke/ink) in two
themes (light/dark).  ``geom`` values feed both the layout engine and the
renderers so column widths always match what is drawn.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = ["Style", "Theme", "Look", "STYLES", "STYLE_ORDER", "get_style"]

STYLE_ORDER = ("quantikz", "qiskit", "modern", "print")


@dataclass(frozen=True)
class Look:
    fill: str
    stroke: str
    ink: str


@dataclass(frozen=True)
class Theme:
    bg: str
    wire: str
    ink: str
    dim: str
    hint: str
    clane: str
    bracket: str


@dataclass(frozen=True)
class Style:
    key: str
    font: str
    fs: float = 13.0  # gate label font size (px)
    pfs: float = 10.5  # parameter line font size
    wire_gap: float = 46.0  # distance between wire centers
    box_h: float = 34.0
    min_col: float = 46.0
    pad: float = 22.0  # horizontal padding inside a gate box
    ctrl_r: float = 4.2  # control-dot radius
    targ_r: float = 9.5  # CNOT target radius
    rx: float = 0.0  # box corner radius
    sw: float = 1.4  # stroke width
    wire_w: float = 1.4
    themes: dict[str, Theme] = field(default_factory=dict)
    palette: dict[str, tuple[str, str]] = field(default_factory=dict)  # family -> (fill, stroke), light
    palette_dark: dict[str, tuple[str, str]] | None = None

    def theme(self, name: str) -> Theme:
        return self.themes.get(name) or self.themes["light"]

    def look(self, theme: Theme, family: str) -> Look:
        """Box colors for a gate family (g1/grot/g2/measure/reset/channel/...)."""
        if not self.palette:
            return Look(fill=theme.bg, stroke=theme.wire, ink=theme.ink)
        pal = self.palette_dark if (theme is self.themes.get("dark") and self.palette_dark) else self.palette
        fill, stroke = pal.get(family, pal["g1"])
        return Look(fill=fill, stroke=stroke, ink=theme.ink)


_SERIF = "Georgia, 'Times New Roman', serif"
_SANS = "'Helvetica Neue', Arial, sans-serif"
_MODERN = "'Inter', 'Segoe UI', system-ui, sans-serif"

STYLES: dict[str, Style] = {
    "quantikz": Style(
        key="quantikz",
        font=_SERIF,
        fs=13.5,
        pfs=10.5,
        themes={
            "light": Theme(
                bg="#ffffff",
                wire="#181b21",
                ink="#101319",
                dim="#5c6673",
                hint="#98a0ad",
                clane="#3c424d",
                bracket="#454c57",
            ),
            "dark": Theme(
                bg="#14171d",
                wire="#e9e7e2",
                ink="#ece9e2",
                dim="#9aa2b0",
                hint="#6e7684",
                clane="#d3d7de",
                bracket="#aab1bd",
            ),
        },
    ),
    "qiskit": Style(
        key="qiskit",
        font=_SANS,
        fs=13.0,
        box_h=36.0,
        rx=2.0,
        ctrl_r=4.5,
        targ_r=10.0,
        themes={
            "light": Theme(
                bg="#ffffff",
                wire="#3b4252",
                ink="#1a1f2b",
                dim="#5b6472",
                hint="#9aa2af",
                clane="#3c424d",
                bracket="#7c66d9",
            ),
            "dark": Theme(
                bg="#10141b",
                wire="#c7cedb",
                ink="#e6eaf2",
                dim="#9aa2b0",
                hint="#6e7684",
                clane="#c3c9d6",
                bracket="#a99af0",
            ),
        },
        palette={
            "g1": ("#dae8fc", "#6c8ebf"),
            "grot": ("#dae8fc", "#6c8ebf"),
            "g2": ("#ffe6cc", "#d79b00"),
            "measure": ("#f5f5f5", "#7f7f7f"),
            "reset": ("#e1d5e7", "#9673a6"),
            "channel": ("#f8cecc", "#b85450"),
            "qram": ("#d5e8d4", "#82b366"),
            "def": ("#fff2cc", "#d6b656"),
            "cop": ("#f5f5f5", "#8a8f99"),
        },
    ),
    "modern": Style(
        key="modern",
        font=_MODERN,
        fs=13.0,
        box_h=36.0,
        wire_gap=48.0,
        min_col=50.0,
        pad=24.0,
        ctrl_r=5.0,
        targ_r=10.5,
        rx=9.0,
        sw=1.6,
        wire_w=1.5,
        themes={
            "light": Theme(
                bg="#ffffff",
                wire="#94a3b8",
                ink="#0f172a",
                dim="#64748b",
                hint="#94a3b8",
                clane="#64748b",
                bracket="#8b5cf6",
            ),
            "dark": Theme(
                bg="#0b1220",
                wire="#3f4b63",
                ink="#e2e8f0",
                dim="#94a3b8",
                hint="#4b5771",
                clane="#8fa0bd",
                bracket="#a78bfa",
            ),
        },
        palette={
            "g1": ("#e0e7ff", "#6366f1"),
            "grot": ("#e0f2fe", "#0284c7"),
            "g2": ("#d1fae5", "#059669"),
            "measure": ("#fef9c3", "#ca8a04"),
            "reset": ("#fce7f3", "#db2777"),
            "channel": ("#fee2e2", "#dc2626"),
            "qram": ("#f3e8ff", "#9333ea"),
            "def": ("#cffafe", "#0891b2"),
            "cop": ("#f1f5f9", "#64748b"),
        },
        palette_dark={
            "g1": ("#312e81cc", "#818cf8"),
            "grot": ("#0c4a6ecc", "#38bdf8"),
            "measure": ("#713f12cc", "#fbbf24"),
            "reset": ("#831843cc", "#f472b6"),
            "channel": ("#7f1d1dcc", "#f87171"),
            "qram": ("#581c87cc", "#c084fc"),
            "def": ("#164e63cc", "#22d3ee"),
            "cop": ("#1e293bcc", "#94a3b8"),
            "g2": ("#064e3bcc", "#34d399"),
        },
    ),
    "print": Style(
        key="print",
        font=_SANS,
        fs=12.0,
        pfs=10.0,
        wire_gap=42.0,
        box_h=30.0,
        min_col=42.0,
        pad=18.0,
        ctrl_r=4.0,
        targ_r=8.5,
        sw=1.2,
        wire_w=1.2,
        themes={
            "light": Theme(
                bg="#ffffff",
                wire="#222222",
                ink="#111111",
                dim="#555555",
                hint="#999999",
                clane="#333333",
                bracket="#555555",
            ),
            "dark": Theme(
                bg="#191919",
                wire="#dddddd",
                ink="#eeeeee",
                dim="#aaaaaa",
                hint="#777777",
                clane="#cccccc",
                bracket="#aaaaaa",
            ),
        },
        palette={
            "g1": ("#ffffff", "#111111"),
            "grot": ("#efefef", "#111111"),
            "g2": ("#d4d4d4", "#111111"),
            "measure": ("#f7f7f7", "#333333"),
            "reset": ("#e3e3e3", "#111111"),
            "channel": ("hatch", "#111111"),
            "qram": ("#9a9a9a", "#111111"),
            "def": ("#ffffff", "#111111"),
            "cop": ("#ffffff", "#555555"),
        },
    ),
}


def get_style(key: str) -> Style:
    """Resolve a style key, raising a helpful error for unknown keys."""
    try:
        return STYLES[key]
    except KeyError:
        raise ValueError(f"Unknown circuit-drawing style {key!r}. Available: {', '.join(STYLE_ORDER)}.") from None
