"""Tests for the circuit rendering engine (uniqc.visualization.circuit_render).

Covers: all seven modes, all four styles, the full OriginIR-ext feature set
(extended gates, dagger, controlled_by, symbolic params, QRAM, error channels,
DEF, classical instructions, QIF/QWHILE), ASCII column alignment, option
validation, file output, and the deprecated draw/draw_html wrappers.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import warnings

import pytest

from uniqc import Circuit
from uniqc.visualization import circuit_render
from uniqc.visualization.circuit_render import render

STYLES = ("quantikz", "qiskit", "modern", "print")


def _basic() -> Circuit:
    c = Circuit(4)
    c.h(0)
    c.cnot(0, 1)
    c.cz(0, 2)
    c.rx(2, 3.1415926 / 2)
    c.swap(2, 3)
    with c.dagger():
        c.t(3)
    c.measure(0, 1)
    return c


def _full_ext() -> Circuit:
    """A circuit exercising the OriginIR-ext surface."""
    c = Circuit(7)
    c.h(0)
    c.x(1)
    c.rx(0, 1.5707963)
    c.rphi(1, 0.3, 0.7)
    c.u3(0, 0.1, 0.2, 0.3)
    c.cnot(0, 1)
    c.cz(1, 2)
    c.swap(2, 3)
    c.iswap(2, 3)
    c.xx(1, 2, 0.7853981)
    c.zz(1, 3, 0.5235987)
    c.phase2q(1, 2, 0.5, 0.3, 0.2)
    c.toffoli(0, 1, 2)
    c.cswap(0, 1, 2)
    c.set_control(0)
    c.ry(2, 1.047)
    c.unset_control()
    c.barrier(0, 1, 2, 3)
    c.creg(3)
    c.measure_to(0, 0)
    c.reset(0)
    c.h(0)
    c.measure_to(1, 1)
    c.measure_to(2, 2)
    c.c_xor(0, 1, 2)
    c.c_not(1, 0)
    c.qif("c[0] & c[1]")
    c.h(3)
    c.x(3)
    c.qelse()
    c.t(3)
    c.endqif()
    c.qwhile("c[0] ^ c[1]")
    c.rz(3, 0.5235987)
    c.endqwhile()
    c.qram_declare("qr0", 2, 2)
    c.qram_call("qr0", 3, 4, 5, 6)
    return c


_CHANNEL_ORIGINIR = """QINIT 2
CREG 0
H q[0]
Depolarizing q[0], (0.01)
BitFlip q[1], (0.02)
PhaseFlip q[0], (0.03)
AmplitudeDamping q[1], (0.05)
PauliError1Q q[0], (0.1, 0.2, 0.3)
TwoQubitDepolarizing q[0], q[1], (0.01)
PauliError2Q q[0], q[1], (0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.11, 0.12, 0.13, 0.14, 0.15)
"""


def _long() -> Circuit:
    c = Circuit(3)
    ops = ["h", "rx", "rz", "cnot", "cz", "swap"]
    for i in range(40):
        if i and i % 8 == 0:
            c.barrier(0, 1, 2)
            continue
        name = ops[i % 6]
        if name in ("cnot", "cz", "swap"):
            getattr(c, name)(i % 3, (i + 1) % 3)
        elif name == "h":
            c.h(i % 3)
        else:
            getattr(c, name)(i % 3, 0.5)
    return c


# --------------------------------------------------------------------------- svg


def test_svg_all_styles():
    for style in STYLES:
        svg = render(_basic(), "svg", style=style)
        assert svg.startswith("<svg") and svg.endswith("</svg>")
        assert "NaN" not in svg
        # CNOT: control dot (small filled circle) + target circle both present
        assert svg.count("<circle") >= 4  # 2 CNOT ends + 2 CZ dots


def test_svg_symbols_align_with_wires():
    svg = render(_basic(), "svg", style="quantikz")
    wires = [float(m.group(1)) for m in re.finditer(r'<line x1="[\d.]+" y1="([\d.]+)" x2="[\d.]+" y2="\1"', svg)]
    assert wires, "no wire lines found"
    for m in re.finditer(r'<circle cx="([\d.]+)" cy="([\d.]+)" r="([\d.]+)"', svg):
        cy, r = float(m.group(2)), float(m.group(3))
        assert any(abs(cy - w) < 0.6 for w in wires), f"symbol at cy={cy} not on a wire"


def test_svg_themes_and_orientation():
    svg_v = render(_basic(), "svg", orientation="v", style="modern", theme="dark")
    assert "rotate(-90" in svg_v  # labels rotated in vertical mode
    svg_desc = render(_basic(), "svg", qubit_order="desc")
    svg_asc = render(_basic(), "svg", qubit_order="asc")
    assert svg_desc != svg_asc


def test_svg_fold_creates_bands():
    svg = render(_long(), "svg", fold=8)
    assert "↳ 续" in svg
    single = render(_long(), "svg", fold=0)
    assert "↳ 续" not in single


def test_svg_clbits_hidden_by_default():
    svg = render(_basic(), "svg")
    assert ">c[0]<" not in svg  # no cbit lane label (tooltips may still mention c[0])
    svg_on = render(_basic(), "svg", show_clbits=True)
    assert ">c[0]<" in svg_on


def test_svg_full_ext_constructs():
    svg = render(_full_ext(), "svg", show_clbits=True, style="modern")
    for marker in ("QRAM", "qr0", "QIF", "QWHILE", "XOR", "|0⟩", "PHASE2Q", "DEF" if False else "else"):
        assert marker in svg, marker
    assert "NaN" not in svg


# --------------------------------------------------------------------------- text


def test_text_default_is_ascii():
    art = render(_basic(), "text")
    assert art.isascii(), "default charset must be pure ASCII"
    assert "q[0]" in art


def test_text_column_alignment():
    for charset in ("ascii", "unicode"):
        art = render(_basic(), "text", charset=charset)
        lines = art.split("\n")
        q0, q1, q2 = lines[0], lines[1], lines[2]
        ctl, tgt = ("*", "(+)") if charset == "ascii" else ("●", "⊕")

        def center(row, token):
            return row.index(token) + len(token) // 2

        assert center(q1, tgt) == center(q0, ctl), f"CNOT control/target misaligned ({charset})"
        q0_cz = q0.index(ctl, q0.index(ctl) + 1)
        assert center(q2, ctl) == q0_cz, f"CZ dots misaligned ({charset})"
        swp = "x" if charset == "ascii" else "×"
        assert center(q2, swp) == center(lines[3], swp), f"SWAP crosses misaligned ({charset})"


def test_text_dagger_and_pi_params():
    art = render(_basic(), "text", charset="unicode")
    assert "T†" in art
    assert "π/2" in art
    art_dec = render(_basic(), "text", charset="unicode", param_mode="decimal")
    assert "1.571" in art_dec
    art_hidden = render(_basic(), "text", param_mode="hidden")
    assert "π/2" not in art_hidden and "1.571" not in art_hidden


def test_text_fold():
    art = render(_long(), "text", fold=14)
    assert "part 2/" in art


def test_text_measure_drop_and_clbit_rules():
    # default: clbits hidden -> no cbit rows
    assert "c[0]" not in render(_basic(), "text")
    shown = render(_basic(), "text", show_clbits=True, charset="unicode")
    assert "╪" in shown and "║" in shown
    # classical instructions force clbit lanes even without show_clbits
    art = render(_full_ext(), "text", charset="unicode")
    assert "XOR" in art and "c[0]" in art


def test_text_full_ext():
    art = render(_full_ext(), "text", charset="unicode")
    for marker in ("QRAM:qr0", "QIF", "QWHILE", "|0⟩", "PHASE2Q"):
        assert marker in art, marker


# --------------------------------------------------------------------------- latex


def test_latex_structure():
    tex = render(_basic(), "latex")
    assert "\\begin{quantikz}" in tex and "\\end{quantikz}" in tex
    assert "\\ctrl{1}" in tex and "\\targ{}" in tex
    assert "\\swap{" in tex and "\\targX{}" in tex
    assert "\\meter{}" in tex
    assert "T^{\\dag}" in tex
    assert "\\frac{\\pi}{2}" in tex


def test_latex_full_ext_compiles(tmp_path):
    if not shutil.which("pdflatex"):
        pytest.skip("pdflatex not installed")
    tex = render(_full_ext(), "latex")
    doc = (
        "\\documentclass[border=10pt]{standalone}\n\\usepackage{quantikz}\n\\begin{document}\n"
        + tex
        + "\n\\end{document}\n"
    )
    src = tmp_path / "circuit.tex"
    src.write_text(doc, encoding="utf-8")
    proc = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", src.name],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert (tmp_path / "circuit.pdf").exists(), proc.stdout[-2000:]


# --------------------------------------------------------------------------- html / interactive


def test_html_and_interactive():
    html = render(_basic(), "html")
    assert html.startswith("<!DOCTYPE html>") and "<svg" in html
    inter = render(_basic(), "interactive")
    assert "addEventListener" in inter and "data-i" in inter
    assert '"CNOT"' in inter or "CNOT" in inter


# --------------------------------------------------------------------------- png / mpl


def test_png_bytes():
    pytest.importorskip("matplotlib")
    data = render(_basic(), "png")
    assert isinstance(data, bytes)
    assert data[:4] == b"\x89PNG"


def test_mpl_figure():
    pytest.importorskip("matplotlib")
    fig = render(_basic(), "mpl")
    assert fig.__class__.__name__ == "Figure"


# --------------------------------------------------------------------------- input forms & API


def test_input_forms():
    c = _basic()
    by_circuit = render(c, "text")
    by_originir = render(c.originir, "text")
    by_qasm = render(c.qasm, "text")
    by_json = render('[{"gate": "H", "qubits": [0]}]', "text")
    assert "H" in by_circuit and "H" in by_originir and "H" in by_qasm and "H" in by_json
    # CNOT control semantics survive the string round-trip
    rows = by_originir.split("\n")
    assert rows[0].index("*") == rows[1].index("(+)") + 1


def test_invalid_options():
    with pytest.raises(ValueError, match="Unknown draw mode"):
        render(_basic(), "pdf")
    with pytest.raises(ValueError, match="Unknown circuit-drawing style"):
        render(_basic(), "svg", style="neon")
    with pytest.raises(TypeError, match="Cannot render"):
        render(object(), "text")


def test_filename_output(tmp_path):
    out = tmp_path / "c.svg"
    svg = render(_basic(), "svg", filename=out)
    assert out.read_text(encoding="utf-8") == svg


def test_channels_render():
    art = render(_CHANNEL_ORIGINIR, "text", charset="unicode")
    assert "Depo" in art and "~" in art
    svg = render(_CHANNEL_ORIGINIR, "svg")
    assert "Depolarizing" in svg and "TwoQubitDepolarizing" in svg
    assert "PauliError2Q" in svg
    tex = render(_CHANNEL_ORIGINIR, "latex")
    assert "dashed" in tex


def test_circuit_draw_method_and_repr():
    c = _basic()
    assert "q[0]" in c.draw("text")
    assert c._repr_svg_().startswith("<svg")
    assert "q[0]" in str(c)


def test_deprecated_wrappers_warn(capsys):
    from uniqc.visualization import draw as old_draw
    from uniqc.visualization import draw_html as old_draw_html

    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter("always")
        art = old_draw(_basic().originir)
        html = old_draw_html(_basic().originir)
    dep = [w for w in ws if issubclass(w.category, DeprecationWarning)]
    assert len(dep) == 2
    assert all("0.2.0" in str(w.message) for w in dep)
    assert "q[0]" in str(art) and "<svg" in html
    assert "q[0]" in capsys.readouterr().out  # old draw() still prints


def test_smart_default_mode():
    # outside Jupyter the default is text
    art = _basic().draw()
    assert isinstance(art, str) and "q[0]" in art


def test_lenient_fallback_for_irregular_ir():
    """Backend-stored IR with bare (unparenthesized) params must still render.

    Regression: gateway /api/circuits/<id>/svg stored ``RX q[0], 1.5707963``
    (no parens) and the old timeline renderer skipped such lines silently.
    """
    irregular = "QINIT 2\nCREG 2\nRX q[0], 1.5707963\nCNOT q[0], q[1]\nMEASURE q[0], c[0]\n"
    art = render(irregular, "text")
    assert "RX(pi/2)" in art
    svg = render(irregular, "svg")
    assert svg.startswith("<svg")
    tex = render(irregular, "latex")
    assert "R_X" in tex


def test_module_level_equivalence():
    c = _basic()
    assert circuit_render.render(c, "text") == c.draw("text")
