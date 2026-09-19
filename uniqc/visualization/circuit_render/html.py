"""HTML wrappers: static (tooltips only) and interactive (click-to-inspect)."""

from __future__ import annotations

import json

from .labels import tooltip
from .model import DrawCircuit
from .options import RenderOptions
from .svg import render_svg

__all__ = ["render_html"]

_PAGE_CSS = """
body{margin:0;font:14px -apple-system,'Segoe UI','PingFang SC',sans-serif;background:#f6f7f9;color:#1c2430}
.wrap{max-width:1180px;margin:0 auto;padding:24px 20px 48px}
h1{font-size:19px;margin:0 0 4px}
.meta{font:12px ui-monospace,monospace;color:#8a93a3;margin-bottom:16px}
.stage{background:#fff;border:1px solid #e3e7ec;border-radius:12px;padding:16px;overflow:auto}
.stage.dark{background:#0b1220;border-color:#1e293b}
.detail{position:sticky;bottom:12px;margin-top:12px;background:#0f172a;color:#c9d5ea;border-radius:10px;
  padding:10px 14px;font:12px ui-monospace,monospace;display:none;white-space:pre-wrap}
"""

_INTERACTIVE_JS = """
document.querySelector('.stage').addEventListener('click', function(e){
  var g = e.target.closest('g.op'); if(!g) return;
  var ops = JSON.parse(document.getElementById('__ops').textContent);
  var op = ops[+g.getAttribute('data-i')];
  var d = document.querySelector('.detail');
  d.style.display = 'block';
  d.textContent = JSON.stringify(op, null, 2);
});
"""


def _op_payload(draw: DrawCircuit) -> list[dict]:
    payload = []
    for op in draw.ops:
        payload.append(
            {
                "op": op.op,
                "qubits": list(op.qubits),
                "cbits": list(op.cbits),
                "params": [str(p) for p in op.params],
                "dagger": op.dagger,
                "controls": list(op.controls),
                **({"name": op.name} if op.name else {}),
                **({"cond": op.cond} if op.cond else {}),
                "text": tooltip(op),
            }
        )
    return payload


def render_html(draw: DrawCircuit, opts: RenderOptions, *, interactive: bool = False) -> str:
    """Render a self-contained HTML document (static or interactive)."""
    svg, meta = render_svg(draw, opts)
    title = "Quantum circuit (interactive)" if interactive else "Quantum circuit"
    detail = ""
    script = ""
    if interactive:
        ops_json = json.dumps(_op_payload(draw), ensure_ascii=False)
        detail = '<div class="detail"></div>'
        script = f'<script type="application/json" id="__ops">{ops_json}</script><script>{_INTERACTIVE_JS}</script>'
    dark = " dark" if opts.theme == "dark" else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{_PAGE_CSS}</style>
</head>
<body>
<div class="wrap">
  <h1>{title}</h1>
  <div class="meta">uniqc · style={opts.style} · theme={opts.theme} · {meta["n_cols"]} columns, folded into {meta["bands"]} band(s)</div>
  <div class="stage{dark}">{svg}</div>
  {detail}
</div>
{script}
</body>
</html>
"""
