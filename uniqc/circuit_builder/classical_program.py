"""Classical / control-flow program tree for OriginIR-ext.

This module extends the flat ``opcode_list`` circuit representation with a
structured program tree expressing mid-circuit measurement, a runtime
classical-register (CREG) store, classical bit instructions, and classical
control flow:

- ``GateOp``      — an ordinary gate / QRAM-call opcode (same tuple layout as
  :data:`uniqc.circuit_builder.qcircuit.OpcodeType`).
- ``MeasureOp``   — ``MEASURE q[i], c[j]``: measure one qubit and write its
  outcome into CREG bit ``j`` (valid both mid-circuit and terminally).
- ``ResetOp``     — ``RESET q[i]``: mid-circuit reset of one qubit to ``|0>``.
- ``ClassicalOp`` — a classical bit instruction ``AND/OR/XOR/MOV/NOT``
  (RISC three-operand, destination-first, non-destructive; operands are CREG
  bits ``c[k]`` or immediates ``0``/``1``).
- ``IfBlock``     — ``QIF <cond> ... [QELSE ...] ENDQIF``.
- ``WhileBlock``  — ``QWHILE <cond> ... ENDQWHILE`` (surface syntax carries no
  iteration bound; the simulator enforces an internal watchdog).

Conditions (:class:`Cond`) are pure boolean logic over single-bit CREG cells:
bit references ``c[i]``, the literals ``0``/``1``, the unary ``not``/``~`` and
the binary ``and``/``&``, ``xor``/``^``, ``or``/``|`` (lowercase keywords and
symbols are interchangeable), with parentheses.  A bare ``c[i]`` is true iff
its bit is ``1``.  Conditions are parsed by :func:`parse_cond` and re-serialized
fully parenthesized with symbol operators for unambiguous round-tripping.

``Circuit`` (see :mod:`uniqc.circuit_builder.qcircuit`) holds a structured
program in ``Circuit.dynamic_program`` (``None`` for ordinary flat circuits).
This module owns serialization (:func:`serialize_program`), parsing
(:func:`parse_program_body`), and a structural deep-copy helper
(:func:`clone_program`).
"""

from __future__ import annotations

__all__ = [
    "Cond",
    "BitRef",
    "ConstBit",
    "NotCond",
    "BinCond",
    "parse_cond",
    "Operand",
    "imm",
    "parse_operand",
    "GateOp",
    "MeasureOp",
    "ResetOp",
    "ClassicalOp",
    "IfBlock",
    "WhileBlock",
    "ProgramNode",
    "CLASSICAL_INSTRUCTIONS",
    "serialize_program",
    "parse_program_body",
    "parse_originir_ext_dynamic",
    "clone_program",
    "contains_dynamic_keywords",
    "DEFAULT_MAX_WHILE_ITERATIONS",
]

import re
from dataclasses import dataclass, field

# Internal QWHILE iteration watchdog default (not part of the surface syntax).
DEFAULT_MAX_WHILE_ITERATIONS = 1_000_000

# Uppercase classical bit instructions and their operand arity (dest excluded).
CLASSICAL_INSTRUCTIONS: dict[str, int] = {"AND": 2, "OR": 2, "XOR": 2, "MOV": 1, "NOT": 1}

# First-token keywords that mark OriginIR-ext text as using the classical /
# control-flow extension (as opposed to a plain flat gate/QRAM circuit).
_DYNAMIC_KEYWORDS = frozenset({"RESET", "QIF", "QELSE", "ENDQIF", "QWHILE", "ENDQWHILE", *CLASSICAL_INSTRUCTIONS})


def contains_dynamic_keywords(originir_str: str) -> bool:
    """Return True if *originir_str* uses the classical / control-flow extension.

    Detects control-flow and classical-instruction keywords, and also
    mid-circuit measurement (a ``MEASURE`` line followed by any later gate /
    classical / control-flow statement — terminal-only measurement does not
    count).
    """
    seen_measure = False
    for raw in originir_str.splitlines():
        line = raw.strip()
        if not line:
            continue
        token = line.split(" ", 1)[0].split("[", 1)[0]
        if token in _DYNAMIC_KEYWORDS:
            return True
        if token == "MEASURE":
            seen_measure = True
            continue
        # A non-header statement appearing after a MEASURE ⇒ mid-circuit measure.
        if seen_measure and token not in ("QINIT", "CREG", "QRAMDECL"):
            return True
    return False


# ---------------------------------------------------------------------------
# Condition AST (boolean logic over single-bit CREG cells)
# ---------------------------------------------------------------------------


class Cond:
    """Base class for classical condition AST nodes."""

    def evaluate(self, creg: list[int]) -> int:
        """Evaluate against *creg* (a list of single-bit ints), returning 0/1."""
        raise NotImplementedError

    def to_str(self) -> str:
        """Serialize to a parseable, fully parenthesized string."""
        raise NotImplementedError

    def __str__(self) -> str:  # pragma: no cover - convenience only
        return self.to_str()


@dataclass(frozen=True)
class BitRef(Cond):
    """A reference to CREG bit ``c[index]`` (true iff the bit is 1)."""

    index: int

    def evaluate(self, creg: list[int]) -> int:
        if self.index >= len(creg) or self.index < 0:
            raise IndexError(f"CREG bit c[{self.index}] is out of range (CREG size {len(creg)}).")
        return 1 if creg[self.index] else 0

    def to_str(self) -> str:
        return f"c[{self.index}]"


@dataclass(frozen=True)
class ConstBit(Cond):
    """A constant bit literal (0 or 1)."""

    value: int

    def evaluate(self, creg: list[int]) -> int:
        return 1 if self.value else 0

    def to_str(self) -> str:
        return str(1 if self.value else 0)


@dataclass(frozen=True)
class NotCond(Cond):
    """Logical/bitwise NOT of a single-bit condition (``~x`` / ``not x``)."""

    operand: Cond

    def evaluate(self, creg: list[int]) -> int:
        return 0 if self.operand.evaluate(creg) else 1

    def to_str(self) -> str:
        return f"~{self.operand.to_str()}"


# Symbol emitted by ``to_str`` for each binary operator (canonical form).
_BIN_SYMBOL = {"and": "&", "xor": "^", "or": "|"}


@dataclass(frozen=True)
class BinCond(Cond):
    """A binary boolean op over single bits: ``and`` (&), ``xor`` (^), ``or`` (|)."""

    op: str  # canonical lowercase keyword: 'and' | 'xor' | 'or'
    left: Cond
    right: Cond

    def evaluate(self, creg: list[int]) -> int:
        a = self.left.evaluate(creg)
        b = self.right.evaluate(creg)
        if self.op == "and":
            return a & b
        if self.op == "or":
            return a | b
        if self.op == "xor":
            return a ^ b
        raise ValueError(f"Unknown binary condition operator: {self.op!r}")

    def to_str(self) -> str:
        return f"({self.left.to_str()} {_BIN_SYMBOL[self.op]} {self.right.to_str()})"


# ---------------------------------------------------------------------------
# Condition tokenizer + precedence-climbing parser
# ---------------------------------------------------------------------------

# Map both symbol and lowercase keyword to the canonical operator name.
_KEYWORD_OPS = {"and": "and", "or": "or", "xor": "xor", "not": "not"}
_SYMBOL_OPS = {"&": "and", "|": "or", "^": "xor", "~": "not"}

_COND_TOKEN_RE = re.compile(
    r"""
    \s*(?:
        (?P<bit>c\s*\[\s*\d+\s*\])
      | (?P<num>[01])
      | (?P<kw>and|or|xor|not)
      | (?P<sym>[&|^~()])
    )
    """,
    re.VERBOSE,
)
_BIT_INDEX_RE = re.compile(r"c\s*\[\s*(\d+)\s*\]")

# Binary operator precedence, low → high (NOT is handled as a prefix op above).
_BIN_PRECEDENCE = {"or": 1, "xor": 2, "and": 3}


def _tokenize_cond(text: str) -> list[tuple[str, str]]:
    """Tokenize a condition string into ``(kind, value)`` tuples."""
    tokens: list[tuple[str, str]] = []
    pos = 0
    n = len(text)
    while pos < n:
        if text[pos].isspace():
            pos += 1
            continue
        m = _COND_TOKEN_RE.match(text, pos)
        if not m or m.end() == pos:
            raise ValueError(f"Cannot tokenize condition at: {text[pos:]!r}")
        if m.group("bit") is not None:
            idx = int(_BIT_INDEX_RE.match(m.group("bit").strip()).group(1))
            tokens.append(("bit", str(idx)))
        elif m.group("num") is not None:
            tokens.append(("num", m.group("num")))
        elif m.group("kw") is not None:
            tokens.append(("op", _KEYWORD_OPS[m.group("kw")]))
        else:
            sym = m.group("sym")
            if sym in _SYMBOL_OPS:
                tokens.append(("op", _SYMBOL_OPS[sym]))
            else:
                tokens.append(("paren", sym))
        pos = m.end()
    return tokens


class _CondParser:
    """Precedence-climbing parser for :class:`Cond`."""

    def __init__(self, tokens: list[tuple[str, str]]):
        self.tokens = tokens
        self.pos = 0

    def _peek(self) -> tuple[str, str] | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _advance(self) -> tuple[str, str]:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def parse(self) -> Cond:
        expr = self._parse_binary(1)
        if self.pos != len(self.tokens):
            raise ValueError(f"Unexpected trailing tokens in condition: {self.tokens[self.pos :]!r}")
        return expr

    def _parse_binary(self, min_prec: int) -> Cond:
        left = self._parse_unary()
        while True:
            tok = self._peek()
            if tok is None or tok[0] != "op" or tok[1] == "not":
                break
            op = tok[1]
            prec = _BIN_PRECEDENCE[op]
            if prec < min_prec:
                break
            self._advance()
            right = self._parse_binary(prec + 1)
            left = BinCond(op, left, right)
        return left

    def _parse_unary(self) -> Cond:
        tok = self._peek()
        if tok is not None and tok[0] == "op" and tok[1] == "not":
            self._advance()
            return NotCond(self._parse_unary())
        return self._parse_atom()

    def _parse_atom(self) -> Cond:
        tok = self._peek()
        if tok is None:
            raise ValueError("Unexpected end of condition.")
        kind, value = tok
        if kind == "paren" and value == "(":
            self._advance()
            expr = self._parse_binary(1)
            nxt = self._peek()
            if nxt is None or nxt != ("paren", ")"):
                raise ValueError("Expected closing parenthesis in condition.")
            self._advance()
            return expr
        if kind == "bit":
            self._advance()
            return BitRef(int(value))
        if kind == "num":
            self._advance()
            return ConstBit(int(value))
        raise ValueError(f"Unexpected token in condition: {tok!r}")


def parse_cond(text) -> Cond:
    """Parse a condition string into a :class:`Cond` AST.

    Accepts CREG bit references ``c[i]``, the literals ``0``/``1``, the unary
    ``not``/``~`` and the binary ``and``/``&``, ``xor``/``^``, ``or``/``|``
    (lowercase keywords and symbols interchangeable), with parentheses.
    Returns *text* unchanged if it is already a :class:`Cond`.
    """
    if isinstance(text, Cond):
        return text
    tokens = _tokenize_cond(str(text))
    if not tokens:
        raise ValueError("Empty condition.")
    return _CondParser(tokens).parse()


# ---------------------------------------------------------------------------
# Classical-instruction operands
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Operand:
    """A classical-instruction source operand: a CREG bit or a 0/1 immediate."""

    is_imm: bool
    value: int  # immediate 0/1 when is_imm else the CREG bit index

    def __post_init__(self) -> None:
        if self.is_imm and self.value not in (0, 1):
            raise ValueError(f"Immediate operand must be 0 or 1, got {self.value!r}.")
        if not self.is_imm and self.value < 0:
            raise ValueError(f"CREG bit index must be non-negative, got {self.value!r}.")

    def read(self, creg: list[int]) -> int:
        if self.is_imm:
            return self.value
        if self.value >= len(creg) or self.value < 0:
            raise IndexError(f"CREG bit c[{self.value}] is out of range (CREG size {len(creg)}).")
        return 1 if creg[self.value] else 0

    def to_str(self) -> str:
        return str(self.value) if self.is_imm else f"c[{self.value}]"


_OPERAND_RE = re.compile(r"^(?:c\s*\[\s*(\d+)\s*\]|([01]))$")


def imm(value: int) -> Operand:
    """Construct an immediate ``0``/``1`` source operand for a classical
    instruction (e.g. ``circuit.c_xor(2, 0, imm(1))`` for ``c[2] = c[0] ^ 1``).

    This disambiguates immediates from CREG bit indices, since a bare ``int``
    passed to the ``Circuit.c_*`` builders denotes a CREG bit index ``c[int]``.
    """
    return Operand(is_imm=True, value=value)


def parse_operand(text: str) -> Operand:
    """Parse a single classical-instruction operand (``c[k]`` or ``0``/``1``)."""
    m = _OPERAND_RE.match(text.strip())
    if not m:
        raise ValueError(f"Invalid classical-instruction operand: {text!r}. Expected c[k] or 0/1.")
    if m.group(1) is not None:
        return Operand(is_imm=False, value=int(m.group(1)))
    return Operand(is_imm=True, value=int(m.group(2)))


# ---------------------------------------------------------------------------
# Program-tree nodes
# ---------------------------------------------------------------------------


@dataclass
class GateOp:
    """An ordinary gate or QRAM-call opcode within a program."""

    opcode: tuple


@dataclass
class MeasureOp:
    """``MEASURE q[qubit], c[cbit]`` — measure *qubit*, write outcome to CREG *cbit*."""

    qubit: int
    cbit: int


@dataclass
class ResetOp:
    """``RESET q[qubit]`` — reset *qubit* to |0>."""

    qubit: int


@dataclass
class ClassicalOp:
    """A classical bit instruction ``AND/OR/XOR/MOV/NOT`` writing CREG bit *dest*."""

    op: str
    dest: int
    srcs: tuple[Operand, ...]

    def __post_init__(self) -> None:
        if self.op not in CLASSICAL_INSTRUCTIONS:
            raise ValueError(f"Unknown classical instruction {self.op!r}.")
        arity = CLASSICAL_INSTRUCTIONS[self.op]
        if len(self.srcs) != arity:
            raise ValueError(f"{self.op} expects {arity} source operand(s), got {len(self.srcs)}.")
        if self.dest < 0:
            raise ValueError(f"Destination CREG bit index must be non-negative, got {self.dest!r}.")

    def evaluate(self, srcs: list[int]) -> int:
        """Compute the destination bit value from already-read *srcs* (0/1)."""
        if self.op == "MOV":
            return srcs[0]
        if self.op == "NOT":
            return 0 if srcs[0] else 1
        a, b = srcs[0], srcs[1]
        if self.op == "AND":
            return a & b
        if self.op == "OR":
            return a | b
        if self.op == "XOR":
            return a ^ b
        raise ValueError(f"Unknown classical instruction {self.op!r}.")

    def execute(self, creg: list[int]) -> int:
        """Read this instruction's source operands from *creg* and return the
        resulting destination bit (0/1). Does not mutate *creg*."""
        return self.evaluate([op.read(creg) for op in self.srcs])


@dataclass
class IfBlock:
    """``QIF <cond> ... [QELSE ...] ENDQIF``."""

    cond: Cond
    then_body: list = field(default_factory=list)
    else_body: list | None = None


@dataclass
class WhileBlock:
    """``QWHILE <cond> ... ENDQWHILE`` (internal watchdog ``max_iterations``)."""

    cond: Cond
    body: list = field(default_factory=list)
    max_iterations: int = DEFAULT_MAX_WHILE_ITERATIONS

    def __post_init__(self) -> None:
        if not isinstance(self.max_iterations, int) or isinstance(self.max_iterations, bool) or self.max_iterations < 1:
            raise ValueError(f"WhileBlock.max_iterations must be a positive integer, got {self.max_iterations!r}.")


ProgramNode = GateOp | MeasureOp | ResetOp | ClassicalOp | IfBlock | WhileBlock


# ---------------------------------------------------------------------------
# Structural clone (used by Circuit.copy())
# ---------------------------------------------------------------------------


def clone_program(nodes: list) -> tuple[list, dict[int, list], dict[int, object]]:
    """Recursively clone a program body list.

    Returns ``(new_list, list_map, node_map)`` where ``list_map`` maps
    ``id(old_list) -> new_list`` for every body list (top-level plus every
    nested if/while body) and ``node_map`` maps ``id(old_node) -> new_node``
    for every ``IfBlock``/``WhileBlock``.  Leaf nodes are recreated as fresh
    value holders.
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
        if isinstance(node, IfBlock):
            new_then = clone_list(node.then_body)
            new_else = clone_list(node.else_body) if node.else_body is not None else None
            new_node = IfBlock(node.cond, new_then, new_else)
            node_map[id(node)] = new_node
            return new_node
        if isinstance(node, WhileBlock):
            new_body = clone_list(node.body)
            new_node = WhileBlock(node.cond, new_body, node.max_iterations)
            node_map[id(node)] = new_node
            return new_node
        if isinstance(node, GateOp):
            return GateOp(node.opcode)
        if isinstance(node, MeasureOp):
            return MeasureOp(node.qubit, node.cbit)
        if isinstance(node, ResetOp):
            return ResetOp(node.qubit)
        if isinstance(node, ClassicalOp):
            return ClassicalOp(node.op, node.dest, tuple(node.srcs))
        raise TypeError(f"Unknown program node: {node!r}")

    new_top = clone_list(nodes)
    return new_top, list_map, node_map


# ---------------------------------------------------------------------------
# Serialization to OriginIR-ext text
# ---------------------------------------------------------------------------


def serialize_program(nodes: list) -> list[str]:
    """Serialize a program body list to OriginIR-ext text lines."""
    from .opcode import opcode_to_line_originir

    lines: list[str] = []
    for node in nodes:
        if isinstance(node, GateOp):
            lines.append(opcode_to_line_originir(node.opcode))
        elif isinstance(node, MeasureOp):
            lines.append(f"MEASURE q[{node.qubit}], c[{node.cbit}]")
        elif isinstance(node, ResetOp):
            lines.append(f"RESET q[{node.qubit}]")
        elif isinstance(node, ClassicalOp):
            operands = ", ".join(op.to_str() for op in node.srcs)
            lines.append(f"{node.op} c[{node.dest}], {operands}")
        elif isinstance(node, IfBlock):
            lines.append(f"QIF {node.cond.to_str()}")
            lines.extend(serialize_program(node.then_body))
            if node.else_body is not None:
                lines.append("QELSE")
                lines.extend(serialize_program(node.else_body))
            lines.append("ENDQIF")
        elif isinstance(node, WhileBlock):
            lines.append(f"QWHILE {node.cond.to_str()}")
            lines.extend(serialize_program(node.body))
            lines.append("ENDQWHILE")
        else:
            raise TypeError(f"Unknown program node: {node!r}")
    return lines


# ---------------------------------------------------------------------------
# Parsing OriginIR-ext program-body text
# ---------------------------------------------------------------------------

_MEASURE_RE = re.compile(r"^MEASURE\s+q\s*\[\s*(\d+)\s*\]\s*,\s*c\s*\[\s*(\d+)\s*\]\s*$")
_RESET_RE = re.compile(r"^RESET\s+q\s*\[\s*(\d+)\s*\]\s*$")
_CLASSICAL_RE = re.compile(r"^(AND|OR|XOR|MOV|NOT)\s+c\s*\[\s*(\d+)\s*\]\s*,\s*(.+)$")
_QIF_RE = re.compile(r"^QIF\s+(.+)$")
_QWHILE_RE = re.compile(r"^QWHILE\s+(.+)$")


def _parse_classical_line(m: re.Match) -> ClassicalOp:
    op = m.group(1)
    dest = int(m.group(2))
    operand_texts = [t.strip() for t in m.group(3).split(",")]
    srcs = tuple(parse_operand(t) for t in operand_texts)
    return ClassicalOp(op, dest, srcs)


def parse_program_body(lines: list[str], start: int = 0) -> tuple[list, int]:
    """Parse a program body starting at ``lines[start]``.

    Stops (without consuming) at a ``QELSE``, ``ENDQIF``, or ``ENDQWHILE`` line
    at this nesting level, or at end of input.  Returns ``(body, next_index)``.

    Ordinary gate / QRAM-call lines are parsed per-line via
    ``OriginIR_LineParser.parse_line``.  Block-form ``CONTROL``/``DAGGER``
    regions are not supported inside a classical program body — use the inline
    ``dagger`` / ``controlled_by(...)`` suffixes instead.
    """
    from uniqc.compile.originir.originir_line_parser import OriginIR_LineParser

    body: list = []
    i = start
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line in ("QELSE", "ENDQIF", "ENDQWHILE"):
            return body, i

        m = _MEASURE_RE.match(line)
        if m:
            body.append(MeasureOp(int(m.group(1)), int(m.group(2))))
            i += 1
            continue

        m = _RESET_RE.match(line)
        if m:
            body.append(ResetOp(int(m.group(1))))
            i += 1
            continue

        m = _CLASSICAL_RE.match(line)
        if m:
            body.append(_parse_classical_line(m))
            i += 1
            continue

        m = _QIF_RE.match(line)
        if m:
            cond = parse_cond(m.group(1))
            then_body, i = parse_program_body(lines, i + 1)
            else_body = None
            if i < len(lines) and lines[i].strip() == "QELSE":
                else_body, i = parse_program_body(lines, i + 1)
            if i >= len(lines) or lines[i].strip() != "ENDQIF":
                raise ValueError(f"QIF at line {i} is missing a matching ENDQIF.")
            i += 1  # consume ENDQIF
            body.append(IfBlock(cond, then_body, else_body))
            continue

        m = _QWHILE_RE.match(line)
        if m:
            cond = parse_cond(m.group(1))
            while_body, i = parse_program_body(lines, i + 1)
            if i >= len(lines) or lines[i].strip() != "ENDQWHILE":
                raise ValueError(f"QWHILE at line {i} is missing a matching ENDQWHILE.")
            i += 1  # consume ENDQWHILE
            body.append(WhileBlock(cond, while_body))
            continue

        # Ordinary gate / QRAM-call line.
        operation, qubits, cbit, parameter, dagger_flag, control_qubits = OriginIR_LineParser.parse_line(line)
        if operation is None:
            i += 1
            continue
        if operation in ("CONTROL", "ENDCONTROL", "DAGGER", "ENDDAGGER"):
            raise ValueError(
                f"Block-form CONTROL/DAGGER regions are not supported inside a classical "
                f"program body (line {i}): {line!r}. Use inline 'dagger'/'controlled_by(...)'."
            )
        body.append(GateOp((operation, qubits, cbit, parameter, dagger_flag, control_qubits)))
        i += 1

    return body, i


# ---------------------------------------------------------------------------
# Top-level OriginIR-ext dynamic-program parser (header + body → Circuit)
# ---------------------------------------------------------------------------


def _replay_body(circuit, nodes: list) -> None:
    """Replay parsed program *nodes* through the ``Circuit`` builder API so
    every normal invariant (record_qubit, block stacks, opcode_list mirroring)
    stays consistent — the same way flat OriginIR parsing replays opcodes
    through ``add_gate``."""
    for node in nodes:
        if isinstance(node, GateOp):
            operation, qubits, cbit, parameter, dagger_flag, control_qubits = node.opcode
            circuit.add_gate(operation, qubits, cbit, parameter, dagger_flag, control_qubits)
        elif isinstance(node, MeasureOp):
            circuit.measure_to(node.qubit, node.cbit)
        elif isinstance(node, ResetOp):
            circuit.reset(node.qubit)
        elif isinstance(node, ClassicalOp):
            circuit._add_classical(node.op, node.dest, node.srcs)
        elif isinstance(node, IfBlock):
            circuit.qif(node.cond)
            _replay_body(circuit, node.then_body)
            if node.else_body is not None:
                circuit.qelse()
                _replay_body(circuit, node.else_body)
            circuit.endqif()
        elif isinstance(node, WhileBlock):
            circuit.qwhile(node.cond, node.max_iterations)
            _replay_body(circuit, node.body)
            circuit.endqwhile()
        else:
            raise TypeError(f"Unknown program node: {node!r}")


def parse_originir_ext_dynamic(originir_str: str):
    """Parse dynamic OriginIR-ext text into a :class:`Circuit`.

    The ``QRAMDECL``/``QINIT``/``CREG`` header is parsed via
    :class:`~uniqc.compile.originir.originir_base_parser.OriginIR_BaseParser`;
    the body (gates, ``MEASURE``/``RESET``, classical instructions, and
    ``QIF``/``QWHILE`` blocks) is parsed via :func:`parse_program_body` and
    replayed through the ``Circuit`` builder API.

    Returns:
        A new ``Circuit`` with its ``dynamic_program`` populated.
    """
    from uniqc.compile.originir.originir_base_parser import OriginIR_BaseParser

    from .qcircuit import Circuit

    lines = originir_str.splitlines()
    header_parser = OriginIR_BaseParser()
    body_start = header_parser._extract_header(lines)
    program, _ = parse_program_body(lines, body_start)

    circuit = Circuit(header_parser.n_qubit)
    circuit.creg(header_parser.n_cbit)
    for name, (addr_size, data_size) in header_parser.qram_declarations.items():
        circuit.qram_declare(name, addr_size, data_size)
    _replay_body(circuit, program)
    return circuit
