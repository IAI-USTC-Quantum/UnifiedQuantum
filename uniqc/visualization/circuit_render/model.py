"""Data model and normalization for circuit rendering.

The render pipeline is::

    Circuit | OriginIR-ext str | OpenQASM str | JSON-ish list
        -> DrawCircuit          (this module)
        -> Layout               (layout.py)
        -> primitives           (svg.py)
        -> svg / text / latex / html / mpl / png

``DrawOp`` mirrors the OriginIR-ext opcode tuple
``(operation, qubits, cbits, params, dagger, controls)`` and adds the
constructs that only exist in the structured program tree
(``MeasureOp``/``ResetOp``/``ClassicalOp``/``IfBlock``/``WhileBlock``) or in
headers (``QRAMDECL``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = ["DrawOp", "DrawCircuit", "to_draw_circuit", "FLOW_OPS", "GREEK_SYMBOL_NAMES"]

FLOW_OPS = frozenset({"QIF", "QELSE", "ENDIF", "QWHILE", "ENDWHILE"})

#: Latin parameter names rendered as Greek letters when the output charset
#: supports it (SVG / HTML / matplotlib / quantikz).
GREEK_SYMBOL_NAMES = {
    "theta": "θ",
    "phi": "φ",
    "alpha": "α",
    "beta": "β",
    "gamma": "γ",
    "lambda": "λ",
    "lam": "λ",
    "mu": "μ",
    "delta": "δ",
    "pi": "π",
}

_SUBSCRIPT_DIGITS = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


@dataclass
class DrawOp:
    """One drawable operation (gate, marker, or classical construct)."""

    op: str
    qubits: tuple[int, ...] = ()
    params: tuple = ()
    cbits: tuple[int, ...] = ()
    dagger: bool = False
    controls: tuple[int, ...] = ()
    name: str | None = None  # CHANNEL / QRAM / DEF / COP display name
    cond: str | None = None  # QIF / QWHILE condition text
    note: str | None = None  # DEF body summary
    addr: int = 0  # QRAM address-bit count
    data: int = 0  # QRAM data-bit count
    raw: str = ""  # original text/IR line, when known
    col: int = -1  # layout column (assigned by layout.py)
    index: int = -1  # index into DrawCircuit.ops (tooltips / interactive)


@dataclass
class DrawCircuit:
    """Normalized, render-ready circuit description."""

    n_qubits: int
    n_cbits: int
    params: list[str] = field(default_factory=list)
    ops: list[DrawOp] = field(default_factory=list)


def display_param(p: Any, *, greek: bool = True) -> str:
    """Render one opcode parameter as display text.

    Numbers are returned unchanged (the caller formats / pi-converts them);
    sympy expressions are stringified with array elements ``alpha_2`` rendered
    as ``alpha[2]`` and common names mapped to Greek letters when *greek*.
    """
    if isinstance(p, (int, float)):
        return p
    text = str(p)
    # sympy prints array elements as ``alpha[2]`` (see Circuit._display_subs);
    # normalize to subscript or bracket form for display.
    if "[" in text and "]" in text:
        base, _, idx = text.partition("[")
        idx = idx.rstrip("]")
        if greek and base in GREEK_SYMBOL_NAMES and idx.isdigit():
            return GREEK_SYMBOL_NAMES[base] + idx.translate(_SUBSCRIPT_DIGITS)
        return f"{GREEK_SYMBOL_NAMES.get(base, base) if greek else base}[{idx}]"
    if greek:
        return GREEK_SYMBOL_NAMES.get(text, text)
    return text


def display_param_ascii(text: str) -> str:
    """ASCII-safe fallback for a display parameter string."""
    table = {
        "π": "pi",
        "θ": "th",
        "φ": "ph",
        "α": "a",
        "β": "b",
        "γ": "g",
        "λ": "l",
        "μ": "u",
        "δ": "d",
        "†": "'",
        "₂": "2",
        "₀": "0",
        "₁": "1",
        "₃": "3",
        "₄": "4",
        "₅": "5",
        "₆": "6",
        "₇": "7",
        "₈": "8",
        "₉": "9",
        "…": "..",
        "≈": "~",
        "←": "<-",
        "⟩": ">",
    }
    for src, dst in table.items():
        text = text.replace(src, dst)
    return text


def _to_int_tuple(value: Any) -> tuple[int, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple, set)):
        return tuple(int(v) for v in value if v is not None)
    return (int(value),)


def _from_opcode_tuple(opcode: tuple, *, qram_names: set[str], raw: str = "") -> DrawOp:
    operation, qubits, cbits, params, dagger, controls = opcode
    name = str(operation)
    if name in qram_names:
        return DrawOp(
            op="QRAM",
            qubits=_to_int_tuple(qubits),
            controls=_to_int_tuple(controls),
            name=name,
            raw=raw or name,
        )
    from uniqc.circuit_builder.originir_spec import available_originir_error_channels

    if name in available_originir_error_channels:
        return DrawOp(
            op="CHANNEL",
            qubits=_to_int_tuple(qubits),
            params=tuple(params)
            if params is not None and hasattr(params, "__len__")
            else (() if params is None else (params,)),
            controls=_to_int_tuple(controls),
            name=name,
            raw=raw,
        )
    return DrawOp(
        op=name,
        qubits=_to_int_tuple(qubits),
        params=tuple(params)
        if params is not None and hasattr(params, "__len__")
        else (() if params is None else (params,)),
        cbits=_to_int_tuple(cbits),
        dagger=bool(dagger),
        controls=_to_int_tuple(controls),
        raw=raw,
    )


def _walk_program(nodes: list, ops: list[DrawOp], qram_names: set[str]) -> None:
    """Flatten a structured ``dynamic_program`` tree into DrawOp markers."""
    from uniqc.circuit_builder.classical_program import (
        ClassicalOp,
        GateOp,
        IfBlock,
        MeasureOp,
        ResetOp,
        WhileBlock,
    )

    for node in nodes:
        if isinstance(node, GateOp):
            ops.append(_from_opcode_tuple(node.opcode, qram_names=qram_names))
        elif isinstance(node, MeasureOp):
            ops.append(DrawOp(op="MEASURE", qubits=(node.qubit,), cbits=(node.cbit,)))
        elif isinstance(node, ResetOp):
            ops.append(DrawOp(op="RESET", qubits=(node.qubit,)))
        elif isinstance(node, ClassicalOp):
            ops.append(
                DrawOp(
                    op="COP",
                    name=node.op,
                    cbits=(node.dest,) + tuple(s.value for s in node.srcs),
                    note=", ".join(s.to_str() for s in node.srcs),
                )
            )
        elif isinstance(node, IfBlock):
            ops.append(DrawOp(op="QIF", cond=node.cond.to_str()))
            _walk_program(node.then_body, ops, qram_names)
            if node.else_body is not None:
                ops.append(DrawOp(op="QELSE"))
                _walk_program(node.else_body, ops, qram_names)
            ops.append(DrawOp(op="ENDIF"))
        elif isinstance(node, WhileBlock):
            ops.append(DrawOp(op="QWHILE", cond=node.cond.to_str()))
            _walk_program(node.body, ops, qram_names)
            ops.append(DrawOp(op="ENDWHILE"))
        else:  # pragma: no cover - defensive
            raise TypeError(f"Unknown program node: {node!r}")


def _from_circuit(circuit: Any) -> DrawCircuit:
    qram_names = set(getattr(circuit, "qram_declarations", {}) or {})
    ops: list[DrawOp] = []
    dynamic = getattr(circuit, "dynamic_program", None)
    if dynamic is not None:
        _walk_program(dynamic, ops, qram_names)
    else:
        for opcode in getattr(circuit, "opcode_list", []) or []:
            ops.append(_from_opcode_tuple(opcode, qram_names=qram_names))
    # Terminal measurements live only in measure_list (never in
    # dynamic_program), while mid-circuit measure_to() lives only in
    # dynamic_program — the two are disjoint, so always append both.
    measure_list = getattr(circuit, "measure_list", None) or []
    for cbit, qubit in enumerate(measure_list):
        ops.append(DrawOp(op="MEASURE", qubits=(int(qubit),), cbits=(cbit,)))
    for name, (addr, data) in getattr(circuit, "qram_declarations", {}).items():
        for op in ops:
            if op.op == "QRAM" and op.name == name:
                op.addr, op.data = addr, data
    import contextlib

    params = []
    with contextlib.suppress(Exception):
        params = list(circuit.free_parameters)
    n_qubits = max(int(getattr(circuit, "qubit_num", 0) or 0), _max_qubit(ops) + 1)
    n_cbits = max(int(getattr(circuit, "cbit_num", 0) or 0), _max_cbit(ops) + 1)
    return DrawCircuit(n_qubits=n_qubits, n_cbits=n_cbits, params=params, ops=ops)


def _max_qubit(ops: list[DrawOp]) -> int:
    best = -1
    for op in ops:
        for q in op.qubits + op.controls:
            best = max(best, q)
    return best


def _max_cbit(ops: list[DrawOp]) -> int:
    best = -1
    for op in ops:
        for c in op.cbits:
            best = max(best, c)
    return best


def _from_jsonable(items: list | dict) -> DrawCircuit:
    if isinstance(items, dict):
        items = [items]
    ops: list[DrawOp] = []
    for entry in items:
        if not isinstance(entry, dict) or not entry:
            continue
        name = str(entry.get("gate", entry.get("op", entry.get("name", "UNKNOWN"))))
        ops.append(
            DrawOp(
                op=name.upper() if name.upper() in FLOW_OPS else name,
                qubits=_to_int_tuple(entry.get("qubits", entry.get("q"))),
                params=tuple(entry.get("params", entry.get("p", ()))),
                cbits=_to_int_tuple(entry.get("cbits", entry.get("c"))),
                dagger=bool(entry.get("dagger", False)),
                controls=_to_int_tuple(entry.get("controls", entry.get("ctrl"))),
                name=entry.get("name"),
                cond=entry.get("cond"),
                addr=int(entry.get("addr", 0)),
                data=int(entry.get("data", 0)),
                raw=str(entry),
            )
        )
    return DrawCircuit(n_qubits=_max_qubit(ops) + 1, n_cbits=_max_cbit(ops) + 1, ops=ops)


def _from_originir_lenient(text: str) -> DrawCircuit:
    """Tolerant line-by-line OriginIR-ext parse; unparseable lines are skipped.

    Used as a fallback when the strict ``Circuit.from_originir`` parse fails —
    e.g. backend-stored IR with bare (unparenthesized) parameters like
    ``RX q[0], 1.5707963``.  Visualization must never crash on slightly
    irregular IR (gateway serves whatever was stored at submit time).
    """
    import re

    from uniqc.compile.originir.originir_line_parser import OriginIR_LineParser

    n_qubits = 0
    n_cbits = 0
    ops: list[DrawOp] = []
    qram_names: set[str] = set()
    qram_sizes: dict[str, tuple[int, int]] = {}
    bare_param_re = re.compile(r"^([A-Za-z][A-Za-z0-9_]*)(\s+q\[[\d,\s]*\]),\s*([-+0-9.eE,\s]+?)\s*$")

    def parse_gate_line(line: str) -> None:
        m = bare_param_re.match(line)
        candidates = [line]
        if m:
            candidates.append(f"{m.group(1)}{m.group(2)}, ({m.group(3)})")
        for cand in candidates:
            try:
                operation, qubits, cbit, params, dagger, controls = OriginIR_LineParser.parse_line(cand)
            except Exception:
                continue
            if operation is None or operation in ("QINIT", "CREG", "CONTROL", "ENDCONTROL", "DAGGER", "ENDDAGGER"):
                return
            ops.append(
                _from_opcode_tuple((operation, qubits, cbit, params, dagger, controls), qram_names=qram_names, raw=line)
            )
            return

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        head = line.split(None, 1)[0].upper()
        if head == "QINIT":
            n_qubits = int(line.split()[1])
            continue
        if head == "CREG":
            n_cbits = int(line.split()[1])
            continue
        if head == "PARAM":
            continue
        if head == "QRAMDECL":
            parts = line.split()
            if len(parts) >= 3:
                name = parts[1]
                nums = re.findall(r"\d+", parts[2])
                addr, data = (int(nums[0]), int(nums[1])) if len(nums) >= 2 else (1, 1)
                qram_names.add(name)
                qram_sizes[name] = (addr, data)
            continue
        m = re.match(r"^MEASURE\s+q\[(\d+)\]\s*,\s*c\[(\d+)\]", line)
        if m:
            ops.append(DrawOp(op="MEASURE", qubits=(int(m.group(1)),), cbits=(int(m.group(2)),), raw=line))
            continue
        m = re.match(r"^RESET\s+q\[(\d+)\]", line)
        if m:
            ops.append(DrawOp(op="RESET", qubits=(int(m.group(1)),), raw=line))
            continue
        m = re.match(r"^(AND|OR|XOR|MOV|NOT)\s+c\[(\d+)\]\s*,\s*(.+)$", line)
        if m:
            srcs = [int(x) for x in re.findall(r"c\[(\d+)\]", m.group(3))]
            ops.append(DrawOp(op="COP", name=m.group(1), cbits=(int(m.group(2)), *srcs), raw=line))
            continue
        if head in ("QIF", "QWHILE"):
            ops.append(DrawOp(op=head, cond=line.split(None, 1)[1] if " " in line else "", raw=line))
            continue
        if head in ("QELSE",):
            ops.append(DrawOp(op="QELSE", raw=line))
            continue
        if head in ("ENDQIF", "ENDIF"):
            ops.append(DrawOp(op="ENDIF", raw=line))
            continue
        if head in ("ENDQWHILE", "ENDWHILE"):
            ops.append(DrawOp(op="ENDWHILE", raw=line))
            continue
        parse_gate_line(line)

    for op in ops:
        if op.op == "QRAM" and op.name in qram_sizes:
            op.addr, op.data = qram_sizes[op.name]
    return DrawCircuit(n_qubits=n_qubits, n_cbits=n_cbits, ops=ops)


def to_draw_circuit(circuit: Any) -> DrawCircuit:
    """Normalize a circuit-like object into a :class:`DrawCircuit`.

    Accepts a :class:`~uniqc.circuit_builder.Circuit`, an OriginIR(-ext) or
    OpenQASM 2.0 string, a JSON string of gate dicts, or a list of gate dicts.
    """
    from uniqc.circuit_builder import Circuit

    if isinstance(circuit, DrawCircuit):
        return circuit
    if isinstance(circuit, Circuit):
        return _from_circuit(circuit)
    if isinstance(circuit, str):
        text = circuit.strip()
        if not text:
            return DrawCircuit(n_qubits=0, n_cbits=0)
        if text.startswith("[") or text.startswith("{"):
            import json

            return _from_jsonable(json.loads(text))
        if text.upper().startswith("OPENQASM"):
            try:
                return _from_circuit(Circuit.from_qasm(text))
            except Exception:
                from uniqc.compile.converter import convert_qasm_to_oir

                return _from_originir_lenient(convert_qasm_to_oir(text))
        try:
            return _from_circuit(Circuit.from_originir(text))
        except Exception:
            return _from_originir_lenient(text)
    if isinstance(circuit, (list, tuple)):
        return _from_jsonable(list(circuit))
    raise TypeError(
        "Cannot render object of type "
        f"{type(circuit).__name__!r}. Expected a uniqc Circuit, an OriginIR/OpenQASM "
        "string, or a JSON list of gate dicts."
    )
