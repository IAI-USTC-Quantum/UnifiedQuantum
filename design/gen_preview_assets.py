#!/usr/bin/env python3
"""Regenerate the *native-format* preview assets embedded in circuit-viz-redesign.html.

Produces, from the page's own live renderer (no duplicated logic):
  - PNG rasters of the `basic` demo circuit in styles A/B/C/D (SVG -> headless Chrome
    screenshot at 2x device scale)            -> {{PNG_quantikz}} ... {{PNG_print}}
  - a real pdflatex + quantikz.sty compile of the generator's LaTeX output
    (PDF -> PNG via pdftoppm)                  -> {{QUANTIKZ_PNG}}

Idempotent: replaces either the {{PLACEHOLDER}} or a previously injected base64 payload,
keyed on the <img alt="..."> name. Requires: node, google-chrome, pdflatex (quantikz), pdftoppm.
"""
import base64
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
HTML = HERE / "circuit-viz-redesign.html"

PNG_SPECS = [  # (alt key, style, theme)
    ("png-quantikz", "quantikz", "light"),
    ("png-qiskit", "qiskit", "light"),
    ("png-modern", "modern", "dark"),
    ("png-print", "print", "light"),
]

NODE_SNIPPET = r"""
const fs = require('fs');
const V = require(process.argv[2]);
const outDir = process.argv[3];
const circ = V.CIRCUITS.basic;
const specs = JSON.parse(process.argv[4]);
for (const [alt, style, theme] of specs) {
  const r = V.renderCircuitSVG(circ, style, {fold: 0, theme, param: 'pi', showClbits: true, scale: 100});
  fs.writeFileSync(outDir + '/' + alt + '.svg', r.svg);
}
fs.writeFileSync(outDir + '/quantikz_basic.tex',
`\\documentclass[border=10pt]{standalone}
\\usepackage{quantikz}
\\begin{document}
` + V.renderQuantikz(circ, {param: 'pi'}) + `
\\end{document}
`);
console.log('node: assets emitted');
"""


def run(cmd, **kw):
    p = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if p.returncode != 0:
        sys.exit(f"FAILED: {' '.join(map(str, cmd))}\n{p.stdout}\n{p.stderr}")
    return p


def main():
    src = HTML.read_text(encoding="utf-8")
    m = re.search(r"<script>\n(.*)\n</script>", src, re.S)
    assert m, "inline <script> not found"
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        core = tdp / "core.js"
        core.write_text(m.group(1), encoding="utf-8")
        (tdp / "emit.js").write_text(NODE_SNIPPET, encoding="utf-8")
        run(["node", str(tdp / "emit.js"), str(core), str(tdp), __import__("json").dumps(PNG_SPECS)])

        b64 = {}
        # --- PNG rasters via headless Chrome (2x device scale) ---
        for alt, style, theme in PNG_SPECS:
            svg = (tdp / f"{alt}.svg").read_text(encoding="utf-8")
            dims = re.search(r'width="([\d.]+)" height="([\d.]+)"', svg)
            w, h = int(float(dims.group(1))), int(float(dims.group(2)))
            bg = "#0b1220" if theme == "dark" else "#ffffff"
            page = tdp / f"{alt}.html"
            page.write_text(
                f'<!doctype html><html><head><style>'
                f'html,body{{margin:0;padding:0;background:{bg};overflow:hidden}}'
                f'::-webkit-scrollbar{{display:none}}</style></head>'
                f'<body>{svg}</body></html>',
                encoding="utf-8")
            out_png = tdp / f"{alt}.png"
            run(["google-chrome", "--headless=new", "--disable-gpu", "--no-sandbox",
                 "--force-device-scale-factor=2", f"--window-size={w},{h}",
                 "--hide-scrollbars",
                 f"--screenshot={out_png}", f"file://{page}"])
            b64[alt] = base64.b64encode(out_png.read_bytes()).decode()

        # --- real quantikz compile ---
        tex = tdp / "quantikz_basic.tex"
        run(["pdflatex", "-interaction=nonstopmode", tex.name], cwd=tdp)
        run(["pdftoppm", "-png", "-r", "170", "-singlefile",
             "quantikz_basic.pdf", "quantikz_basic"], cwd=tdp)
        b64["quantikz-compiled"] = base64.b64encode((tdp / "quantikz_basic.png").read_bytes()).decode()

    replaced = 0
    for alt, payload in b64.items():
        pat = re.compile(r'(<img alt="' + re.escape(alt) + r'" src="data:image/png;base64,)[^"]*(")')
        src, n = pat.subn(lambda mm: mm.group(1) + payload + mm.group(2), src)
        assert n == 1, f"placeholder for {alt} not found ({n} matches)"
        replaced += 1
    HTML.write_text(src, encoding="utf-8")
    print(f"embedded {replaced} preview assets into {HTML.name}")


if __name__ == "__main__":
    main()
