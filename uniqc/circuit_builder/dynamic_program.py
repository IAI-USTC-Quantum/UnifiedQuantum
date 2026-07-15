"""Structured dynamic program AST for OriginIR-ext.

This module extends the flat ``opcode_list`` circuit representation with a
structured program tree that can express mid-circuit control flow:

- ``GateNode``   — an ordinary gate/QRAM-call opcode (same tuple layout as
  :data:`uniqc.circuit_builder.qcircuit.OpcodeType`).
- ``CMeasureNode`` — mid-circuit measurement of one qubit into a named
  classical-memory register (distinct from the terminal ``MEASURE ...,
  c[...]`` statement, which always targets the classical register array).
- ``ResetNode``  — mid-circuit reset of one qubit to ``|0>``.
- ``AssignNode`` — classical assignment ``mem = expr``.
- ``IfNode``     — ``QIF cond ... [ELSE ...] ENDQIF``.
- ``WhileNode``  — ``QWHILE cond, max_iterations ... ENDQWHILE``.

Classical expressions (``Expr``) support integer/comparison/logical
arithmetic over named classical-memory registers, parsed from a small infix
grammar (``parse_expr``) and always re-serialized fully parenthesized for
unambiguous round-tripping (``Expr.to_str``).

``Circuit`` (see :mod:`uniqc.circuit_builder.qcircuit`) holds a structured
program in ``Circuit.dynamic_program`` (``None`` for ordinary flat circuits)
built via ``Circuit.qif``/``qelse``/``endqif``/``qwhile``/``endqwhile``/
``cmeasure``/``reset_qubit``/``cassign``/``declare_memory``. This module owns
serialization (:func:`serialize_program`) and parsing
(:func:`parse_dynamic_body`) of the corresponding OriginIR-ext text, plus a
structural deep-copy helper (:func:`clone_program`) used by ``Circuit.copy()``.
"""

from __future__ import annotations

__all__ = [
    "Expr",
    "ConstExpr",
    "MemExpr",
    "UnaryExpr",
    "BinExpr",
    "parse_expr",
    "GateNode",
    "CMeasureNode",
    "ResetNode",
    "AssignNode",
    "IfNode",
    "WhileNode",
    "DynamicNode",
    "serialize_program",
    "clone_program",
    "parse_dynamic_body",
    "parse_originir_ext_dynamic",
    "contains_dynamic_keywords",
    "DEFAULT_MAX_WHILE_ITERATIONS",
]

import re
from dataclasses import dataclass, field

DEFAULT_MAX_WHILE_ITERATIONS = 10_000

# Keywords that identify OriginIR-ext text as using the dynamic-program
# extension (as opposed to a plain flat gate/QRAM/CONTROL/DAGGER circuit).
_DYNAMIC_KEYWORDS = ("CDECL", "CMEASURE", "RESET", "CASSIGN", "QIF", "QWHILE")


def contains_dynamic_keywords(originir_str: str) -> bool:
    """Return True if *originir_str* uses any dynamic-program keyword."""
    for line in originir_str.splitlines():
        token = line.strip().split(" ", 1)[0] if line.strip() else ""
        if token in _DYNAMIC_KEYWORDS:
            return True
    return False


# ---------------------------------------------------------------------------
# Classical expression AST
# ---------------------------------------------------------------------------


class Expr:
    """Base class for classical expression AST nodes."""

    def evaluate(self, memory: dict[str, int]) -> int:
        """Evaluate this expression against *memory*, returning an int."""
        raise NotImplementedError

    def to_str(self) -> str:
        """Serialize back to a parseable, fully parenthesized string."""
        raise NotImplementedError

    def __str__(self) -> str:  # pragma: no cover - convenience only
        return self.to_str()


@dataclass(frozen=True)
class ConstExpr(Expr):
    """An integer literal."""

    value: int

    def evaluate(self, memory: dict[str, int]) -> int:
        return self.value

    def to_str(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class MemExpr(Expr):
    """A reference to a named classical-memory register."""

    name: str

    def evaluate(self, memory: dict[str, int]) -> int:
        if self.name not in memory:
            raise KeyError(
                f"Unknown classical memory '{self.name}'. Call Circuit.declare_memory() before referencing it."
            )
        return memory[self.name]

    def to_str(self) -> str:
        return self.name


_UNARY_OPS = {
    "-": lambda a: -a,
    "!": lambda a: 0 if a else 1,
}

_BIN_OPS = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "/": lambda a, b: _int_div(a, b),
    "%": lambda a, b: _int_mod(a, b),
    "==": lambda a, b: int(a == b),
    "!=": lambda a, b: int(a != b),
    "<": lambda a, b: int(a < b),
    "<=": lambda a, b: int(a <= b),
    ">": lambda a, b: int(a > b),
    ">=": lambda a, b: int(a >= b),
    "&&": lambda a, b: int(bool(a) and bool(b)),
    "||": lambda a, b: int(bool(a) or bool(b)),
}


def _int_div(a: int, b: int) -> int:
    if b == 0:
        raise ZeroDivisionError("Classical expression division by zero.")
    # Truncate toward zero (C-like), not Python's floor division.
    q = abs(a) // abs(b)
    return -q if (a < 0) != (b < 0) else q


def _int_mod(a: int, b: int) -> int:
    if b == 0:
        raise ZeroDivisionError("Classical expression modulo by zero.")
    return a - _int_div(a, b) * b


@dataclass(frozen=True)
class UnaryExpr(Expr):
    """A unary operation: ``-x`` or ``!x``."""

    op: str
    operand: Expr

    def evaluate(self, memory: dict[str, int]) -> int:
        return _UNARY_OPS[self.op](self.operand.evaluate(memory))

    def to_str(self) -> str:
        return f"({self.op}{self.operand.to_str()})"


@dataclass(frozen=True)
class BinExpr(Expr):
    """A binary operation, e.g. ``a + b`` or ``a == b``."""

    op: str
    left: Expr
    right: Expr

    def evaluate(self, memory: dict[str, int]) -> int:
        return _BIN_OPS[self.op](self.left.evaluate(memory), self.right.evaluate(memory))

    def to_str(self) -> str:
        return f"({self.left.to_str()} {self.op} {self.right.to_str()})"


# ---------------------------------------------------------------------------
# Expression tokenizer + recursive-descent parser
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(
    r"""
    \s*(?:
        (?P<num>\d+)
      | (?P<id>[A-Za-z_][A-Za-z0-9_]*)
      | (?P<op>==|!=|<=|>=|&&|\|\||[-+*/%<>!()])
    )
    """,
    re.VERBOSE,
)


def _tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    pos = 0
    while pos < len(text):
        if text[pos].isspace():
            pos += 1
            continue
        m = _TOKEN_RE.match(text, pos)
        if not m or m.end() == pos:
            raise ValueError(f"Cannot tokenize classical expression at: {text[pos:]!r}")
        tokens.append(m.group().strip())
        pos = m.end()
    return tokens


class _ExprParser:
    """Recursive-descent / precedence-climbing parser for :class:`Expr`."""

    # Precedence, low to high.
    _PRECEDENCE = {
        "||": 1,
        "&&": 2,
        "==": 3,
        "!=": 3,
        "<": 4,
        "<=": 4,
        ">": 4,
        ">=": 4,
        "+": 5,
        "-": 5,
        "*": 6,
        "/": 6,
        "%": 6,
    }

    def __init__(self, tokens: list[str]):
        self.tokens = tokens
        self.pos = 0

    def _peek(self) -> str | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _advance(self) -> str:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def parse(self) -> Expr:
        expr = self._parse_binary(0)
        if self.pos != len(self.tokens):
            raise ValueError(f"Unexpected trailing tokens in expression: {self.tokens[self.pos :]!r}")
        return expr

    def _parse_binary(self, min_prec: int) -> Expr:
        left = self._parse_unary()
        while True:
            op = self._peek()
            if op not in self._PRECEDENCE or self._PRECEDENCE[op] < min_prec:
                break
            self._advance()
            next_min_prec = self._PRECEDENCE[op] + 1
            right = self._parse_binary(next_min_prec)
            left = BinExpr(op, left, right)
        return left

    def _parse_unary(self) -> Expr:
        tok = self._peek()
        if tok in ("-", "!"):
            self._advance()
            return UnaryExpr(tok, self._parse_unary())
        return self._parse_atom()

    def _parse_atom(self) -> Expr:
        tok = self._peek()
        if tok is None:
            raise ValueError("Unexpected end of expression.")
        if tok == "(":
            self._advance()
            expr = self._parse_binary(0)
            if self._peek() != ")":
                raise ValueError("Expected closing parenthesis in expression.")
            self._advance()
            return expr
        if tok.isdigit():
            self._advance()
            return ConstExpr(int(tok))
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", tok):
            self._advance()
            return MemExpr(tok)
        raise ValueError(f"Unexpected token in expression: {tok!r}")


def parse_expr(text: str) -> Expr:
    """Parse a classical expression string into an :class:`Expr` AST.

    Supports integer literals, classical-memory identifiers, arithmetic
    (``+ - * / %``, truncating-toward-zero division), comparisons
    (``== != < <= > >=``), logical operators (``&& || !``), unary minus, and
    parentheses.
    """
    tokens = _tokenize(text)
    if not tokens:
        raise ValueError("Empty classical expression.")
    return _ExprParser(tokens).parse()


# ---------------------------------------------------------------------------
# Dynamic program nodes
# ---------------------------------------------------------------------------


@dataclass
class GateNode:
    """An ordinary gate or QRAM-call opcode within a dynamic program."""

    opcode: tuple


@dataclass
class CMeasureNode:
    """Mid-circuit measurement of *qubit* into classical memory *mem*."""

    qubit: int
    mem: str


@dataclass
class ResetNode:
    """Mid-circuit reset of *qubit* to |0>."""

    qubit: int


@dataclass
class AssignNode:
    """Classical assignment: ``mem = expr``."""

    mem: str
    expr: Expr


@dataclass
class IfNode:
    """``QIF cond ... [ELSE ...] ENDQIF``."""

    cond: Expr
    then_body: list = field(default_factory=list)
    else_body: list | None = None


@dataclass
class WhileNode:
    """``QWHILE cond, max_iterations ... ENDQWHILE``."""

    cond: Expr
    body: list = field(default_factory=list)
    max_iterations: int = DEFAULT_MAX_WHILE_ITERATIONS

    def __post_init__(self) -> None:
        if not isinstance(self.max_iterations, int) or isinstance(self.max_iterations, bool) or self.max_iterations < 1:
            raise ValueError(f"WhileNode.max_iterations must be a positive integer, got {self.max_iterations!r}.")


DynamicNode = GateNode | CMeasureNode | ResetNode | AssignNode | IfNode | WhileNode


# ---------------------------------------------------------------------------
# Structural clone (used by Circuit.copy())
# ---------------------------------------------------------------------------


def clone_program(nodes: list) -> tuple[list, dict[int, list], dict[int, object]]:
    """Recursively clone a dynamic-program body list.

    Returns ``(new_list, list_map, node_map)``:

    - ``list_map`` maps ``id(old_list) -> new_list`` for every body list
      encountered (the top-level list plus every nested if/while body).
    - ``node_map`` maps ``id(old_node) -> new_node`` for every ``IfNode``/
      ``WhileNode`` encountered.

    Leaf nodes (``GateNode``/``CMeasureNode``/``ResetNode``/``AssignNode``)
    are immutable value holders and are shared rather than duplicated.
    """
    list_map: dict[int, list] = {}
    node_map: dict[int, object] = {}

    def clone_list(old_list: list) -> list:
        new_list: list = []
        list_map[id(old_list)] = new_list
        for node in old_list:
            new_list.append(clone_node(node))
        return new_list

    def clone_node(node):
        if isinstance(node, IfNode):
            new_then = clone_list(node.then_body)
            new_else = clone_list(node.else_body) if node.else_body is not None else None
            new_node = IfNode(node.cond, new_then, new_else)
            node_map[id(node)] = new_node
            return new_node
        if isinstance(node, WhileNode):
            new_body = clone_list(node.body)
            new_node = WhileNode(node.cond, new_body, node.max_iterations)
            node_map[id(node)] = new_node
            return new_node
        return node

    new_top = clone_list(nodes)
    return new_top, list_map, node_map


# ---------------------------------------------------------------------------
# Serialization to OriginIR-ext text
# ---------------------------------------------------------------------------


def serialize_program(nodes: list) -> list[str]:
    """Serialize a dynamic-program body list to OriginIR-ext text lines."""
    from .opcode import opcode_to_line_originir

    lines: list[str] = []
    for node in nodes:
        if isinstance(node, GateNode):
            lines.append(opcode_to_line_originir(node.opcode))
        elif isinstance(node, CMeasureNode):
            lines.append(f"CMEASURE q[{node.qubit}], {node.mem}")
        elif isinstance(node, ResetNode):
            lines.append(f"RESET q[{node.qubit}]")
        elif isinstance(node, AssignNode):
            lines.append(f"CASSIGN {node.mem}, {node.expr.to_str()}")
        elif isinstance(node, IfNode):
            lines.append(f"QIF {node.cond.to_str()}")
            lines.extend(serialize_program(node.then_body))
            if node.else_body is not None:
                lines.append("ELSE")
                lines.extend(serialize_program(node.else_body))
            lines.append("ENDQIF")
        elif isinstance(node, WhileNode):
            lines.append(f"QWHILE {node.cond.to_str()}, {node.max_iterations}")
            lines.extend(serialize_program(node.body))
            lines.append("ENDQWHILE")
        else:
            raise TypeError(f"Unknown dynamic program node: {node!r}")
    return lines


# ---------------------------------------------------------------------------
# Parsing OriginIR-ext dynamic-program text
# ---------------------------------------------------------------------------

_CDECL_RE = re.compile(r"^CDECL\s+([A-Za-z_][A-Za-z0-9_]*)\s*,\s*(-?\d+)\s*$")
_CMEASURE_RE = re.compile(r"^CMEASURE\s+q\s*\[\s*(\d+)\s*\]\s*,\s*([A-Za-z_][A-Za-z0-9_]*)\s*$")
_RESET_RE = re.compile(r"^RESET\s+q\s*\[\s*(\d+)\s*\]\s*$")
_CASSIGN_RE = re.compile(r"^CASSIGN\s+([A-Za-z_][A-Za-z0-9_]*)\s*,\s*(.+)$")
_QIF_RE = re.compile(r"^QIF\s+(.+)$")
_QWHILE_RE = re.compile(r"^QWHILE\s+(.+)$")


def _split_qwhile_header(text: str) -> tuple[str, int]:
    """Split ``"<cond>, <max_iterations>"`` from a QWHILE header.

    The condition expression may itself contain commas only inside balanced
    parentheses, so the trailing top-level comma (outside all parens) is the
    separator for the max-iterations integer.
    """
    depth = 0
    for i in range(len(text) - 1, -1, -1):
        ch = text[i]
        if ch == ")":
            depth += 1
        elif ch == "(":
            depth -= 1
        elif ch == "," and depth == 0:
            cond_text = text[:i].strip()
            max_iter_text = text[i + 1 :].strip()
            if not max_iter_text.lstrip("-").isdigit():
                raise ValueError(f"Invalid QWHILE max_iterations: {max_iter_text!r}")
            max_iterations = int(max_iter_text)
            if max_iterations < 1:
                raise ValueError(f"QWHILE max_iterations must be a positive integer, got {max_iterations}.")
            return cond_text, max_iterations
    raise ValueError(f"QWHILE header missing ', max_iterations': {text!r}")


def parse_dynamic_body(
    lines: list[str],
    start: int,
    qram_names: set[str],
    top_level: bool = False,
) -> tuple[list, int]:
    """Parse a dynamic-program body starting at ``lines[start]``.

    Stops (without consuming) at a line that is ``ELSE``, ``ENDQIF``, or
    ``ENDQWHILE`` at this nesting level, or at end of input. When
    *top_level* is True, also stops (without consuming) at the first
    terminal ``MEASURE q[..], c[..]`` line, since terminal measurement is
    only valid after the dynamic program body, never nested inside a
    QIF/QWHILE block.

    Returns ``(body, next_index)``.

    Ordinary gate/QRAM-call lines (including inline ``dagger`` /
    ``controlled_by(...)`` suffixes) are parsed per-line via
    ``OriginIR_LineParser.parse_line`` — block-form ``CONTROL``/``DAGGER``
    regions are not supported inside dynamic-program bodies in this stage.
    """
    from uniqc.compile.originir.originir_line_parser import OriginIR_LineParser

    body: list = []
    i = start
    while i < len(lines):
        raw = lines[i]
        line = raw.strip()
        if not line:
            i += 1
            continue
        if line in ("ELSE", "ENDQIF", "ENDQWHILE"):
            return body, i
        if top_level and line.split()[0] == "MEASURE":
            return body, i

        m = _CMEASURE_RE.match(line)
        if m:
            body.append(CMeasureNode(int(m.group(1)), m.group(2)))
            i += 1
            continue

        m = _RESET_RE.match(line)
        if m:
            body.append(ResetNode(int(m.group(1))))
            i += 1
            continue

        m = _CASSIGN_RE.match(line)
        if m:
            body.append(AssignNode(m.group(1), parse_expr(m.group(2))))
            i += 1
            continue

        m = _QIF_RE.match(line)
        if m:
            cond = parse_expr(m.group(1))
            then_body, i = parse_dynamic_body(lines, i + 1, qram_names)
            else_body = None
            if i < len(lines) and lines[i].strip() == "ELSE":
                else_body, i = parse_dynamic_body(lines, i + 1, qram_names)
            if i >= len(lines) or lines[i].strip() != "ENDQIF":
                raise ValueError(f"QIF at line {i} is missing a matching ENDQIF.")
            i += 1  # consume ENDQIF
            body.append(IfNode(cond, then_body, else_body))
            continue

        m = _QWHILE_RE.match(line)
        if m:
            cond_text, max_iterations = _split_qwhile_header(m.group(1))
            cond = parse_expr(cond_text)
            while_body, i = parse_dynamic_body(lines, i + 1, qram_names)
            if i >= len(lines) or lines[i].strip() != "ENDQWHILE":
                raise ValueError(f"QWHILE at line {i} is missing a matching ENDQWHILE.")
            i += 1  # consume ENDQWHILE
            body.append(WhileNode(cond, while_body, max_iterations))
            continue

        # Ordinary gate / QRAM-call line.
        operation, qubits, cbit, parameter, dagger_flag, control_qubits = OriginIR_LineParser.parse_line(line)
        if operation is None:
            i += 1
            continue
        if operation == "MEASURE":
            raise ValueError(
                f"Terminal MEASURE is not allowed inside a QIF/QWHILE body (line {i}): {line!r}. "
                "Use CMEASURE for mid-circuit measurement into classical memory."
            )
        if operation in ("CONTROL", "ENDCONTROL", "DAGGER", "ENDDAGGER"):
            raise ValueError(
                f"Block-form CONTROL/DAGGER regions are not supported inside dynamic-program "
                f"bodies (line {i}): {line!r}. Use inline 'dagger'/'controlled_by(...)' suffixes."
            )
        body.append(GateNode((operation, qubits, cbit, parameter, dagger_flag, control_qubits)))
        i += 1

    return body, i


# ---------------------------------------------------------------------------
# Top-level OriginIR-ext dynamic-program parser (header + body + measure)
# ---------------------------------------------------------------------------

_QINIT_RE = re.compile(r"^QINIT\s+(\d+)\s*$")
_CREG_RE = re.compile(r"^CREG\s+(\d+)\s*$")
_QRAMDECL_RE = re.compile(r"^QRAMDECL\s+([A-Za-z_][A-Za-z0-9_]*)\s+(\d+)\s*,\s*(\d+)\s*$")
_MEASURE_RE = re.compile(r"^MEASURE\s+q\s*\[\s*(\d+)\s*\]\s*,\s*c\s*\[\s*(\d+)\s*\]\s*$")


def _replay_body(circuit, nodes: list) -> None:
    """Replay parsed dynamic-program *nodes* through the ``Circuit`` builder
    API, so every normal invariant (record_qubit, block stacks, opcode_list
    mirroring) stays consistent — the same way flat OriginIR parsing replays
    opcodes through ``add_gate``."""
    for node in nodes:
        if isinstance(node, GateNode):
            operation, qubits, cbit, parameter, dagger_flag, control_qubits = node.opcode
            circuit.add_gate(operation, qubits, cbit, parameter, dagger_flag, control_qubits)
        elif isinstance(node, CMeasureNode):
            circuit.cmeasure(node.qubit, node.mem)
        elif isinstance(node, ResetNode):
            circuit.reset_qubit(node.qubit)
        elif isinstance(node, AssignNode):
            circuit.cassign(node.mem, node.expr)
        elif isinstance(node, IfNode):
            circuit.qif(node.cond)
            _replay_body(circuit, node.then_body)
            if node.else_body is not None:
                circuit.qelse()
                _replay_body(circuit, node.else_body)
            circuit.endqif()
        elif isinstance(node, WhileNode):
            circuit.qwhile(node.cond, max_iterations=node.max_iterations)
            _replay_body(circuit, node.body)
            circuit.endqwhile()
        else:
            raise TypeError(f"Unknown dynamic program node: {node!r}")


def parse_originir_ext_dynamic(originir_str: str):
    """Parse an OriginIR-ext string containing dynamic-program constructs.

    Handles the same ``QRAMDECL``/``CDECL`` header lines, ``QINIT``/``CREG``
    declarations, and trailing terminal ``MEASURE`` lines as the flat parser,
    but parses the circuit body as a structured dynamic program (see
    :func:`parse_dynamic_body`) and rebuilds the ``Circuit`` by replaying it
    through the same builder API used for programmatic construction.

    Returns:
        Circuit: A new ``Circuit`` with ``dynamic_program`` populated.
    """
    from .qcircuit import Circuit

    lines = originir_str.strip().splitlines()

    qram_declarations: dict[str, tuple[int, int]] = {}
    classical_memory: dict[str, int] = {}
    n_qubit = None
    n_cbit = None
    i = 0

    def _consume_header_line(line: str) -> str | None:
        """Try to consume a QRAMDECL/CDECL header line; return None if consumed,
        otherwise return the unmatched line for the caller to handle."""
        m = _QRAMDECL_RE.match(line)
        if m:
            qram_declarations[m.group(1)] = (int(m.group(2)), int(m.group(3)))
            return None
        m = _CDECL_RE.match(line)
        if m:
            classical_memory[m.group(1)] = int(m.group(2))
            return None
        return line

    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if _consume_header_line(line) is None:
            i += 1
            continue
        m = _QINIT_RE.match(line)
        if m:
            n_qubit = int(m.group(1))
            i += 1
            break
        raise ValueError(f"Expected QRAMDECL/CDECL/QINIT before circuit body, got: {line!r}")

    if n_qubit is None:
        raise ValueError("OriginIR-ext input is missing a QINIT statement.")

    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if _consume_header_line(line) is None:
            i += 1
            continue
        m = _CREG_RE.match(line)
        if m:
            n_cbit = int(m.group(1))
            i += 1
            break
        raise ValueError(f"Expected QRAMDECL/CDECL/CREG after QINIT, got: {line!r}")

    if n_cbit is None:
        raise ValueError("OriginIR-ext input is missing a CREG statement.")

    from uniqc.compile.originir.originir_line_parser import OriginIR_LineParser

    OriginIR_LineParser._declared_qram_names = set(qram_declarations.keys())

    body, i = parse_dynamic_body(lines, i, set(qram_declarations.keys()), top_level=True)

    measure_qubits: list[tuple[int, int]] = []
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        m = _MEASURE_RE.match(line)
        if not m:
            raise ValueError(f"Unexpected line after dynamic program body: {line!r}")
        measure_qubits.append((int(m.group(1)), int(m.group(2))))
        i += 1

    circuit = Circuit()
    for name, (addr_size, data_size) in qram_declarations.items():
        circuit.qram_declarations[name] = (addr_size, data_size)
    for name, init in classical_memory.items():
        circuit.declare_memory(name, init)

    _replay_body(circuit, body)

    if measure_qubits:
        cbits_used = sorted(cbit for _, cbit in measure_qubits)
        if cbits_used != list(range(len(measure_qubits))):
            raise ValueError(
                "Terminal MEASURE classical-bit targets must form a canonical, "
                f"contiguous c[0..{len(measure_qubits) - 1}] mapping with no gaps or "
                "duplicates — Circuit only supports sequential cbit assignment "
                "(cbit = position in measurement order), so a non-canonical mapping "
                f"cannot be preserved. Got: {sorted(measure_qubits, key=lambda item: item[1])!r}."
            )
        measured = [qubit for qubit, _ in sorted(measure_qubits, key=lambda item: item[1])]
        circuit.measure(*measured)

    # QINIT may declare more qubits than are actually referenced by any
    # gate/measurement (e.g. trailing idle qubits) — widen to match, mirroring
    # what the declared header promises, without shrinking usage-inferred width.
    circuit.qubit_num = max(circuit.qubit_num, n_qubit)
    circuit.max_qubit = max(circuit.max_qubit, n_qubit - 1)
    circuit.cbit_num = n_cbit
    return circuit
