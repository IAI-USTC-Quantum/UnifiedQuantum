"""OriginIR base parser module.

This module provides the base parser for OriginIR quantum circuit representation,
including parsing QINIT, CREG statements and quantum operations.

OriginIR-ext supports **named quantum/classical registers**. ``QINIT`` and
``CREG`` accept either the classic bare-integer form (``QINIT 6`` ≡
``QINIT q[6]``, ``CREG 6`` ≡ ``CREG c[6]``) or one or more named-register
declarations, written either as multiple lines or as a single comma-separated
line (``QINIT q[6], q1[6]``). Registers are laid into a single flat physical
index space in declaration order (so ``QINIT q[6]`` followed by
``QINIT q1[6]`` is equivalent to ``QINIT 12`` with ``q`` → 0–5 and ``q1`` →
6–11). Register-qualified references (``q1[0]``, ``c1[2]``) are resolved to
physical indices at parse time; the parser (and ``to_extended_originir``) always
emit a flat single ``QINIT``/``CREG`` header with physical ``q[i]``/``c[i]``
operands — register names are not preserved on export.

``DEF`` subroutines reuse the named-register declaration syntax for their
formal signature (``DEF name(q[2], anc[1]) (theta1, theta2)``) with an optional
trailing list of **scalar** parameter names. Calls (``name(a[3], a[5]) (0.5)``)
are expanded inline into the flat program at parse time.

Key exports:
    OriginIR_BaseParser: Base parser class for OriginIR circuits.
"""

__all__ = ["OriginIR_BaseParser"]

import re
from copy import deepcopy

from uniqc.circuit_builder import opcode_to_line_originir
from uniqc.circuit_builder.qcircuit import Circuit

from .originir_line_parser import OriginIR_LineParser

# A register reference/declaration item: ``name[index]`` (or ``name[size]``).
_REG_ITEM_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*) *\[ *(\d+) *\]")
_REG_ITEM_FULL_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*) *\[ *(\d+) *\] *$")
_IDENT_FULL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_INT_FULL_RE = re.compile(r"^\d+$")


class _DefInfo:
    """A parsed ``DEF`` subroutine definition.

    Attributes:
        name: Subroutine name.
        formal_base: Mapping of formal register name -> ``(local_base, size)``,
            laid out contiguously in declaration order.
        total_qubits: Total number of formal qubits (sum of register sizes).
        params: Ordered list of scalar parameter names.
        body_lines: Raw (unresolved) body lines, verbatim from the source.
    """

    __slots__ = ("name", "formal_base", "total_qubits", "params", "body_lines")

    def __init__(self, name, formal_base, total_qubits, params, body_lines):
        self.name = name
        self.formal_base = formal_base
        self.total_qubits = total_qubits
        self.params = params
        self.body_lines = body_lines


class OriginIR_BaseParser:
    """Parser for OriginIR quantum circuit representation.

    Attributes:
        n_qubit: Total number of qubits (sum over all quantum registers).
        n_cbit: Total number of classical bits (sum over all classical registers).
        program_body: List of operation opcodes (flat, register-resolved).
        raw_originir: Raw OriginIR string.
        measure_qubits: List of measurement tuples (qubit, cbit).
        qram_declarations: Mapping of QRAM name -> (addr_size, data_size).
        qreg_map: Mapping of quantum register name -> (base_index, size).
        creg_map: Mapping of classical register name -> (base_index, size).
        gate_definitions: Mapping of DEF name -> :class:`_DefInfo`.
    """

    def __init__(self):
        self.n_qubit = None
        self.n_cbit = None
        self.program_body = []
        self.raw_originir = None
        self.measure_qubits: list[tuple[int, int]] = []
        self.qram_declarations: dict[str, tuple[int, int]] = {}
        # Named-register maps: name -> (base_index, size).
        self.qreg_map: dict[str, tuple[int, int]] = {}
        self.creg_map: dict[str, tuple[int, int]] = {}
        # DEF subroutine definitions.
        self.gate_definitions: dict[str, _DefInfo] = {}
        # Symbolic-parameter arrays declared via ``PARAM name[size]``.
        self._param_arrays: dict[str, int] = {}
        # Running totals used while laying registers into the flat index space.
        self._qtotal = 0
        self._ctotal = 0
        # Parse-time control/dagger state.
        self._control_qubits_set: set[int] = set()
        self._dagger_stack: list[list] = []
        self._dagger_count = 0

    # ------------------------------------------------------------------
    # Register declaration handling
    # ------------------------------------------------------------------

    def _add_qreg(self, name: str, size: int) -> None:
        if name in self.qreg_map:
            raise ValueError(f"Duplicate quantum register '{name}'.")
        if name in self.creg_map:
            raise ValueError(f"Register name '{name}' is used for both a quantum and a classical register.")
        self.qreg_map[name] = (self._qtotal, size)
        self._qtotal += size

    def _add_creg(self, name: str, size: int) -> None:
        if name in self.creg_map:
            raise ValueError(f"Duplicate classical register '{name}'.")
        if name in self.qreg_map:
            raise ValueError(f"Register name '{name}' is used for both a quantum and a classical register.")
        self.creg_map[name] = (self._ctotal, size)
        self._ctotal += size

    @staticmethod
    def _parse_register_decl(arg_str: str, default_name: str, kind: str) -> list[tuple[str, int]]:
        """Parse the argument portion of a QINIT/CREG line.

        Supports the bare-integer form (``6`` -> default register) and the
        named / comma-separated form (``q[6], q1[6]``).
        """
        s = arg_str.strip()
        if s == "":
            raise ValueError(f"{kind} declaration is empty.")
        if _INT_FULL_RE.match(s):
            return [(default_name, int(s))]
        decls: list[tuple[str, int]] = []
        for item in s.split(","):
            item = item.strip()
            if not item:
                continue
            m = _REG_ITEM_FULL_RE.match(item)
            if not m:
                raise ValueError(
                    f"Invalid {kind} register declaration item '{item}'. Expected a bare integer or 'name[size]'."
                )
            decls.append((m.group(1), int(m.group(2))))
        if not decls:
            raise ValueError(f"Invalid {kind} declaration: '{arg_str}'.")
        return decls

    def _extract_header(self, lines: list[str]) -> int:
        """Consume the QRAMDECL/QINIT/CREG header and return the body start index."""
        idx = 0
        n = len(lines)
        seen_qinit = False
        seen_creg = False
        while idx < n:
            raw = lines[idx].strip()
            if not raw:
                idx += 1
                continue
            token = raw.split()[0]
            if token == "QRAMDECL":
                _op, name, addr_size, data_size = OriginIR_LineParser.handle_qramdecl(raw)
                if name in self.qram_declarations:
                    raise ValueError(f"QRAM '{name}' is declared more than once.")
                self.qram_declarations[name] = (addr_size, data_size)
                OriginIR_LineParser._declared_qram_names.add(name)
                idx += 1
                continue
            if token == "QINIT":
                if seen_creg:
                    raise ValueError("QINIT declarations must precede CREG declarations.")
                for reg_name, size in self._parse_register_decl(raw[len("QINIT") :], "q", "QINIT"):
                    self._add_qreg(reg_name, size)
                seen_qinit = True
                idx += 1
                continue
            if token == "CREG":
                for reg_name, size in self._parse_register_decl(raw[len("CREG") :], "c", "CREG"):
                    self._add_creg(reg_name, size)
                seen_creg = True
                idx += 1
                continue
            if token == "PARAM":
                self._handle_param_decl(raw)
                idx += 1
                continue
            # First line that is not part of the header — the body starts here.
            break

        if not seen_qinit:
            raise ValueError("OriginIR input does not have correct QINIT statement.")
        if not seen_creg:
            raise ValueError("OriginIR input does not have correct CREG statement.")

        self.n_qubit = self._qtotal
        self.n_cbit = self._ctotal
        return idx

    def _handle_param_decl(self, raw: str) -> None:
        """Parse a ``PARAM name`` (scalar) or ``PARAM name[size]`` (array) line.

        Array declarations are recorded so the resulting circuit re-serializes
        with the same ``PARAM name[size]`` header and renders element symbols as
        ``name[i]``.  Scalar declarations are validated but need no state — the
        symbol is created when the parameter is referenced in a gate line.
        """
        arg = raw[len("PARAM") :].strip()
        array_match = _REG_ITEM_FULL_RE.match(arg)
        if array_match:
            name, size = array_match.group(1), int(array_match.group(2))
            if name in self._param_arrays and self._param_arrays[name] != size:
                raise ValueError(f"Conflicting PARAM array declaration for '{name}'.")
            self._param_arrays[name] = size
            return
        if _IDENT_FULL_RE.match(arg):
            return
        raise ValueError(f"Invalid PARAM declaration: {raw!r}")

    # ------------------------------------------------------------------
    # Reference resolution
    # ------------------------------------------------------------------

    def _resolve_line_registers(self, line: str, lineno: int) -> str:
        """Rewrite register-qualified references in *line* to physical indices.

        Named registers (``regname[idx]``) are resolved to the canonical
        physical registers ``q[<physical>]`` / ``c[<physical>]`` with strict
        parse-time range checks. References to the canonical physical registers
        ``q`` / ``c`` themselves are passed through unchanged (identity
        resolution): they are already physical, and their range is validated by
        the standard operation-qubit check downstream — matching the historical
        (register-less) parser behaviour.
        """

        def repl(m: "re.Match") -> str:
            name, idx = m.group(1), int(m.group(2))
            # Canonical physical registers: pass through unchanged.
            if name == "q" or name == "c":
                return m.group(0)
            if name in self.qreg_map:
                base, size = self.qreg_map[name]
                if idx >= size:
                    raise ValueError(
                        f"Parse error at line {lineno}: {line}\n"
                        f"Index {idx} is out of range for quantum register '{name}' (size {size})."
                    )
                return f"q[{base + idx}]"
            if name in self.creg_map:
                base, size = self.creg_map[name]
                if idx >= size:
                    raise ValueError(
                        f"Parse error at line {lineno}: {line}\n"
                        f"Index {idx} is out of range for classical register '{name}' (size {size})."
                    )
                return f"c[{base + idx}]"
            # A declared symbolic-parameter array reference (``alpha[2]``): leave
            # it verbatim so the parameter parser can turn it into symbol
            # ``alpha_2`` — it is not a qubit/classical register.
            if name in self._param_arrays:
                return m.group(0)
            raise ValueError(f"Parse error at line {lineno}: {line}\nUnknown register '{name}'.")

        return _REG_ITEM_RE.sub(repl, line)

    def _resolve_qubit_ref(self, name: str, idx: int, lineno: int, physical: bool) -> int:
        if physical:
            if name != "q":
                raise ValueError(f"Parse error at line {lineno}: unexpected register '{name}' in expanded call.")
            return idx
        if name in self.qreg_map:
            base, size = self.qreg_map[name]
            if idx >= size:
                raise ValueError(
                    f"Parse error at line {lineno}: index {idx} out of range for quantum register '{name}' "
                    f"(size {size})."
                )
            return base + idx
        # ``q`` is the canonical physical register even when only named
        # registers were declared: allow direct physical addressing.
        if name == "q":
            if self.n_qubit is not None and idx >= self.n_qubit:
                raise ValueError(
                    f"Parse error at line {lineno}: physical qubit q[{idx}] exceeds the maximum (QINIT {self.n_qubit})."
                )
            return idx
        raise ValueError(f"Parse error at line {lineno}: unknown quantum register '{name}'.")

    def _resolve_whole_register(self, name: str, lineno: int, physical: bool) -> list[int]:
        if physical:
            raise ValueError(f"Parse error at line {lineno}: whole-register argument '{name}' is not allowed here.")
        if name in self.qreg_map:
            base, size = self.qreg_map[name]
            return list(range(base, base + size))
        raise ValueError(f"Parse error at line {lineno}: unknown quantum register '{name}'.")

    def _resolve_call_qubits(self, qargs: str, name: str, lineno: int, physical: bool) -> list[int]:
        result: list[int] = []
        for item in qargs.split(","):
            item = item.strip()
            if not item:
                continue
            m = _REG_ITEM_FULL_RE.match(item)
            if m:
                result.append(self._resolve_qubit_ref(m.group(1), int(m.group(2)), lineno, physical))
            elif _IDENT_FULL_RE.match(item):
                result.extend(self._resolve_whole_register(item, lineno, physical))
            else:
                raise ValueError(f"Parse error at line {lineno}: invalid qubit argument '{item}' in call to '{name}'.")
        return result

    @staticmethod
    def _resolve_call_params(pargs, name: str, lineno: int) -> list[float]:
        if pargs is None or pargs.strip() == "":
            return []
        values: list[float] = []
        for tok in pargs.split(","):
            tok = tok.strip()
            if not tok:
                continue
            try:
                values.append(float(tok))
            except ValueError as exc:
                raise ValueError(
                    f"Parse error at line {lineno}: non-scalar parameter '{tok}' in call to '{name}'."
                ) from exc
        return values

    # ------------------------------------------------------------------
    # DEF handling
    # ------------------------------------------------------------------

    def _collect_def_block(self, lines: list[str], start: int) -> int:
        """Collect a ``DEF ... ENDDEF`` block and return the next line index."""
        header = lines[start].strip()
        _op, formal_qregs, params, name = OriginIR_LineParser.handle_def(header)

        formal_base: dict[str, tuple[int, int]] = {}
        base = 0
        for reg_name, size in formal_qregs:
            if reg_name in formal_base:
                raise ValueError(f"Duplicate register '{reg_name}' in DEF '{name}' signature.")
            formal_base[reg_name] = (base, size)
            base += size
        total = base

        for param in params:
            if param in formal_base:
                raise ValueError(f"DEF '{name}': parameter '{param}' collides with a register name.")

        body: list[str] = []
        i = start + 1
        closed = False
        while i < len(lines):
            body_line = lines[i].strip()
            if body_line == "ENDDEF":
                closed = True
                break
            if body_line.split()[:1] == ["DEF"]:
                raise ValueError(f"Nested DEF definitions are not supported (in DEF '{name}').")
            if body_line:
                body.append(body_line)
            i += 1
        if not closed:
            raise ValueError(f"DEF '{name}' block is not closed with ENDDEF.")

        if name in self.gate_definitions:
            raise ValueError(f"Duplicate DEF definition '{name}'.")
        if name in self.qram_declarations or name in OriginIR_LineParser._declared_qram_names:
            raise ValueError(f"DEF name '{name}' collides with a QRAM declaration.")
        self.gate_definitions[name] = _DefInfo(name, formal_base, total, params, body)
        return i + 1  # skip the ENDDEF line

    def _instantiate_def_line(self, body_line, definition, actual_qubits, param_values):
        line = body_line
        # 1) Substitute scalar parameters (whole-word) with numeric literals.
        for pname, pval in param_values.items():
            line = re.sub(rf"\b{re.escape(pname)}\b", repr(float(pval)), line)

        # 2) Rewrite formal register references to physical ``q[<actual>]``.
        def repl(m: "re.Match") -> str:
            reg_name, idx = m.group(1), int(m.group(2))
            if reg_name not in definition.formal_base:
                raise ValueError(
                    f"Parse error in DEF '{definition.name}': unknown register '{reg_name}' in body: {body_line}"
                )
            base, size = definition.formal_base[reg_name]
            if idx >= size:
                raise ValueError(
                    f"Parse error in DEF '{definition.name}': index {idx} out of range for register "
                    f"'{reg_name}' (size {size})."
                )
            return f"q[{actual_qubits[base + idx]}]"

        return _REG_ITEM_RE.sub(repl, line)

    def _expand_def_call(self, name: str, qubits: list[int], params: list[float], lineno: int) -> None:
        definition = self.gate_definitions[name]
        if len(qubits) != definition.total_qubits:
            raise ValueError(
                f"Parse error at line {lineno}: DEF '{name}' expects {definition.total_qubits} qubit(s), "
                f"got {len(qubits)}."
            )
        if len(params) != len(definition.params):
            raise ValueError(
                f"Parse error at line {lineno}: DEF '{name}' expects {len(definition.params)} parameter(s), "
                f"got {len(params)}."
            )
        param_values = dict(zip(definition.params, params, strict=True))
        for body_line in definition.body_lines:
            expanded = self._instantiate_def_line(body_line, definition, qubits, param_values)
            self._process_statement(expanded, lineno, physical=True)

    # ------------------------------------------------------------------
    # Statement processing
    # ------------------------------------------------------------------

    def _process_statement(self, line: str, lineno: int, physical: bool) -> None:
        """Resolve and dispatch a single (non-DEF-header) statement."""
        # DEF subroutine call?
        call_match = OriginIR_LineParser.regexp_defcall.match(line)
        if call_match and call_match.group(1) in self.gate_definitions:
            name = call_match.group(1)
            qubits = self._resolve_call_qubits(call_match.group(2), name, lineno, physical)
            params = self._resolve_call_params(call_match.group(3), name, lineno)
            self._expand_def_call(name, qubits, params, lineno)
            return

        # Ordinary statement: resolve register references unless already physical.
        if not physical:
            line = self._resolve_line_registers(line, lineno)

        operation, qubits, cbit, parameter, dagger_flag, control_qubits = OriginIR_LineParser.parse_line(line)
        if operation is None:
            return
        if operation in ("QINIT", "CREG"):
            raise ValueError(f"Parse error at line {lineno}: '{operation}' may only appear in the header.")
        self._apply_op(operation, qubits, cbit, parameter, dagger_flag, control_qubits, line, lineno)

    def _apply_op(self, operation, qubits, cbit, parameter, dagger_flag, control_qubits, line, lineno) -> None:
        # QRAMDECL encountered in the body — register it and continue.
        if operation == "QRAMDECL":
            name, addr_size, data_size = qubits
            if name in self.qram_declarations:
                raise ValueError(f"Parse error at line {lineno}: QRAM '{name}' is declared more than once.")
            self.qram_declarations[name] = (addr_size, data_size)
            OriginIR_LineParser._declared_qram_names.add(name)
            return

        # Range checks for operational qubit(s) and cbit.
        if isinstance(qubits, list):
            for qubit in qubits:
                if qubit >= self.n_qubit:
                    raise ValueError(
                        f"Parse error at line {lineno}: {line}\nQubit exceeds the maximum (QINIT {self.n_qubit})."
                    )
        elif qubits and qubits >= self.n_qubit:
            raise ValueError(f"Parse error at line {lineno}: {line}\nQubit exceeds the maximum (QINIT {self.n_qubit}).")

        for control_qubit in control_qubits or []:
            if control_qubit >= self.n_qubit:
                raise ValueError(
                    f"Parse error at line {lineno}: {line}\n"
                    f"Control qubit exceeds the maximum (QINIT {self.n_qubit})."
                )

        if cbit and cbit >= self.n_cbit:
            raise ValueError(f"Parse error at line {lineno}: {line}\nCbit exceeds the maximum (CBIT {self.n_cbit}).")

        if operation == "CONTROL":
            self._control_qubits_set.update(qubits)
        elif operation == "ENDCONTROL":
            for qubit in qubits:
                self._control_qubits_set.discard(qubit)
        elif operation == "DAGGER":
            self._dagger_stack.append([])
            self._dagger_count += 1
        elif operation == "ENDDAGGER":
            if self._dagger_stack:
                reversed_ops = self._dagger_stack.pop()
                if not self._dagger_stack:
                    self.program_body.extend(reversed_ops[::-1])
                else:
                    self._dagger_stack[-1].extend(reversed_ops[::-1])
            else:
                raise ValueError(
                    f"Parse error at line {lineno}: {line}\nEncounter ENDDAGGER operation before any DAGGER."
                )
            self._dagger_count -= 1
        else:
            if operation == "MEASURE":
                if self._control_qubits_set:
                    raise ValueError(
                        f"Parse error at line {lineno}: {line}\nMEASURE operation is inside a CONTROL block."
                    )
                if self._dagger_stack:
                    raise ValueError(
                        f"Parse error at line {lineno}: {line}\nMEASURE operation is inside a DAGGER block."
                    )
                self.measure_qubits.append((qubits, cbit))
            else:
                dagger_flag = dagger_flag ^ bool(self._dagger_count % 2)

                ctrl_qubits = deepcopy(self._control_qubits_set)
                for qubit in control_qubits:
                    if qubit in ctrl_qubits:
                        raise ValueError(
                            f"Parse error at line {lineno}: {line}\n"
                            f"Qubit {qubit} is duplicated in the CONTROL statement."
                        )
                    ctrl_qubits.add(qubit)

                qubits_used = deepcopy(ctrl_qubits)
                if isinstance(qubits, int):
                    if qubits in ctrl_qubits:
                        raise ValueError(
                            f"Parse error at line {lineno}: {line}\n"
                            f"Qubit {qubits} is duplicated in the CONTROL statement."
                        )
                else:
                    for qubit in qubits:
                        if qubit in ctrl_qubits:
                            raise ValueError(
                                f"Parse error at line {lineno}: {line}\n"
                                f"Qubit {qubit} is duplicated in the CONTROL statement."
                            )
                        qubits_used.add(qubit)

                ctrl_list = sorted(ctrl_qubits) if ctrl_qubits else None
                if self._dagger_stack:
                    self._dagger_stack[-1].append((operation, qubits, cbit, parameter, dagger_flag, ctrl_list))
                else:
                    self.program_body.append((operation, qubits, cbit, parameter, dagger_flag, ctrl_list))

    # ------------------------------------------------------------------
    # Top-level parse
    # ------------------------------------------------------------------

    def parse(self, originir_str):
        """Parse an OriginIR string and populate internal state.

        Args:
            originir_str: OriginIR string to parse.
        """
        self.raw_originir = originir_str

        lines = originir_str.strip().splitlines()
        if not lines:
            raise ValueError("Parse error. Input is empty.")

        # Reset QRAM name registry for this parse session.
        OriginIR_LineParser._declared_qram_names = set()

        current_lineno = self._extract_header(lines)

        # Re-register declared QRAM names for this parse session.
        OriginIR_LineParser._declared_qram_names = set(self.qram_declarations.keys())

        self._control_qubits_set = set()
        self._dagger_stack = []
        self._dagger_count = 0

        lineno = current_lineno
        while lineno < len(lines):
            raw = lines[lineno].strip()
            if not raw:
                lineno += 1
                continue
            token = raw.split()[0]
            if token == "DEF":
                lineno = self._collect_def_block(lines, lineno)
                continue
            if raw == "ENDDEF":
                raise ValueError(f"Parse error at line {lineno}: {raw}\nENDDEF without a matching DEF.")
            self._process_statement(raw, lineno, physical=False)
            lineno += 1

        # Finally, check if all dagger and control operations are closed.
        if self._control_qubits_set:
            raise ValueError("Parse error at end.\nThe CONTROL operation is not closed at the end of the OriginIR.")
        if self._dagger_stack:
            raise ValueError("Parse error at end.\nThe DAGGER operation is not closed at the end of the OriginIR.")

    def to_extended_originir(self):
        """Convert parsed data back to extended OriginIR string.

        The output is always **flat**: a single ``QINIT``/``CREG`` header with
        physical ``q[i]``/``c[i]`` operands (named registers and DEF blocks are
        resolved/inlined at parse time).

        Returns:
            str: Extended OriginIR string representation.
        """
        ret = ""
        for name, (addr_size, data_size) in self.qram_declarations.items():
            ret += f"QRAMDECL {name} {addr_size},{data_size}\n"
        ret += f"QINIT {self.n_qubit}\n"
        ret += f"CREG {self.n_cbit}\n"
        body_lines = [opcode_to_line_originir(opcode) for opcode in self.program_body]
        ret += "\n".join(body_lines)
        if body_lines:
            ret += "\n"
        for qubit, cbit in sorted(self.measure_qubits, key=lambda item: item[1]):
            ret += f"MEASURE q[{qubit}], c[{cbit}]\n"
        return ret

    @property
    def originir(self):
        """OriginIR string representation (alias for to_extended_originir).

        Returns:
            str: Extended OriginIR string.
        """
        return self.to_extended_originir()

    def __str__(self):
        return self.to_extended_originir()

    def to_circuit(self) -> Circuit:
        """
        The function coverts OriginIR string into uniqc.Circuit object.

        Returns:
            uniqc.Circuit object.
        """
        circuit = Circuit()

        # Transfer QRAM declarations
        for name, (addr_size, data_size) in self.qram_declarations.items():
            circuit.qram_declarations[name] = (addr_size, data_size)

        # Transfer symbolic-parameter array declarations (PARAM name[size]).
        circuit._param_arrays = dict(self._param_arrays)

        for opcode in self.program_body:
            operation, qubits, cbit, parameter, dagger_flag, control_qubits = opcode
            circuit.add_gate(operation, qubits, cbit, parameter, dagger_flag, control_qubits)

        if self.measure_qubits:
            measured_qubits = [qubit for qubit, _ in sorted(self.measure_qubits, key=lambda item: item[1])]
            circuit.measure(*measured_qubits)
        if self.n_cbit is not None:
            circuit.cbit_num = self.n_cbit

        return circuit

    def to_qasm(self):
        """
        The function coverts OriginIR string into OpenQASM string.

        Returns:
            OpenQASM string.
        """
        circuit = self.to_circuit()
        return circuit.qasm
