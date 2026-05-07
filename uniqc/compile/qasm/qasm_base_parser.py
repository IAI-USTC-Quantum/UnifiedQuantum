"""OpenQASM 2.0 base parser module.

This module provides the base parser for OpenQASM 2.0 quantum circuit representation,
including parsing qreg/creg definitions, quantum operations, and measurement statements.

Key exports:
    OpenQASM2_BaseParser: Base parser class for OpenQASM 2.0 circuits.
"""

__all__ = ["OpenQASM2_BaseParser"]
from typing import List, Tuple
from uniqc.circuit_builder.qcircuit import Circuit
from uniqc.compile.originir.originir_base_parser import OriginIR_BaseParser
from uniqc.circuit_builder.translate_qasm2_oir import get_opcode_from_QASM2
from .qasm_line_parser import OpenQASM2_LineParser
from .exceptions import NotSupportedGateError, RegisterDefinitionError, RegisterNotFoundError, RegisterOutOfRangeError


class OpenQASM2_BaseParser:
    """Parser for OpenQASM 2.0 quantum circuit representation.

    Attributes:
        qregs: List of quantum register tuples (name, size).
        cregs: List of classical register tuples (name, size).
        n_qubit: Total number of qubits.
        n_cbit: Total number of classical bits.
        program_body: List of operation opcodes.
        measure_qubits: List of measurement tuples (qubit, cbit).
    """

    def __init__(self):
        self.qregs = list()
        self.cregs = list()        
        self.n_qubit = None
        self.n_cbit = None
        self.program_body = list() # contain the opcodes
        self.raw_qasm = None
        self.formatted_qasm = None

        # for qasm statement collection
        self.collected_qregs_str = list()
        self.collected_cregs_str = list()
        self.collected_measurements_str = list()
        self.program_body_str = list() # contain strs of the program body

        # for measurement mapping
        self.measure_qubits : List[Tuple[int, int]] = list()

    def _format_and_check(self):
        '''Format the original qasm code and check if it is valid.

           As of v0.0.11.dev23, the parser **inlines** user-defined
           ``gate <name>(<params>) <args> { <body> }`` blocks: each call
           to such a gate in the program body is expanded into a sequence
           of primitive gate calls with parameters and qubit arguments
           substituted.  Gate names that match a known qelib1.inc / OriginIR
           opcode are still recognised directly via the gate-name → opcode
           table in ``translate_qasm2_oir``.  Inline ``opaque`` declarations
           are stripped (no body to inline).  ``if`` statements are still
           not supported.

           A canonical format of qasm code is like:
           OPENQASM 2.0;
           include "qelib1.inc";

           qreg q[n];
           <other qreg definitions>
           creg c[m];
           <other creg definitions>
           <program_body>

           These rules will be applied in the formatted qasm code.
           1. OPENQASM 2.0 and include "qelib1.inc" will be removed.
           2. ``gate ... { ... }`` definitions are stripped (their bodies are
              not expanded; recognition relies on the gate-name registry).
           3. qreg definitions are collected together; so as creg definitions.
           4. program body is line-wise, separated by semicolons
           5. measurements must be at the end of the program body.
           6. barriers are kept in the program body.
        '''
        if self.raw_qasm is None:
            raise ValueError("No raw qasm code provided.")

        import re

        # ------------------------------------------------------------------
        # Extract user-defined gate bodies BEFORE stripping the def blocks.
        # We support the common form:
        #     gate <name>(<param1>, <param2>, ...) <arg1>, <arg2>, ... { <body> }
        # or the parameter-less:
        #     gate <name> <arg1>, <arg2>, ... { <body> }
        # The body is split on ';' into individual statements that will be
        # substituted in-place when the gate is called.
        # ``opaque`` declarations have no body and are simply stripped.
        # ------------------------------------------------------------------
        gate_def_re = re.compile(
            r"\bgate\s+([A-Za-z_][A-Za-z0-9_]*)"          # 1: gate name
            r"(?:\s*\(([^)]*)\))?"                          # 2: optional params
            r"\s+([A-Za-z_][A-Za-z0-9_,\s]*)"             # 3: qubit args
            r"\s*\{([^{}]*)\}",                              # 4: body
            flags=re.MULTILINE | re.DOTALL,
        )
        gate_defs: dict[str, tuple[list[str], list[str], list[str]]] = {}
        for m in gate_def_re.finditer(self.raw_qasm):
            name = m.group(1).strip()
            params_str = (m.group(2) or "").strip()
            args_str = m.group(3).strip()
            body_str = m.group(4).strip()

            params = [p.strip() for p in params_str.split(",") if p.strip()]
            args = [a.strip() for a in args_str.split(",") if a.strip()]
            body_lines = [s.strip() for s in body_str.split(";") if s.strip()]
            gate_defs[name] = (params, args, body_lines)

        self._gate_defs = gate_defs  # exposed for tests / introspection

        # Strip both opaque decls and gate-def blocks now that we've collected them.
        def _strip_gate_defs(src: str) -> str:
            # gate ... { ... } block (matches the same shape we collected)
            src = gate_def_re.sub("", src)
            # opaque ... ;  (no body)
            src = re.sub(
                r"\bopaque\b\s+[A-Za-z_][A-Za-z0-9_]*"
                r"(?:\s*\([^)]*\))?\s*[^;{]*;",
                "",
                src,
                flags=re.MULTILINE | re.DOTALL,
            )
            return src

        raw = _strip_gate_defs(self.raw_qasm)

        # check if there is "if" statements (use word boundary regex to avoid
        # false positives on substrings like "Unified" that contain "if").
        if re.search(r"\bif\s*\(", raw):
            raise NotSupportedGateError("If statements are not supported yet.")
        
        collected_qregs = list()
        collected_cregs = list()
        collected_measurements = list()
        program_body = list()

        # split all codes by semicolons (use the gate-def-stripped source)
        codes = raw.split(';')
        for code in codes:
            # strip leading and trailing whitespaces
            code = code.strip()
            # remove comments and OPENQASM/include statements
            if code.startswith('//'):
                continue
            elif code == '':
                continue
            elif code.startswith('include'):
                continue
            elif code.startswith('OPENQASM'):
                continue
            # handle qreg and creg definitions
            elif code.startswith('qreg'):
                collected_qregs.append(code)
            elif code.startswith('creg'):
                collected_cregs.append(code)
            elif code.startswith('measure'):
                collected_measurements.append(code)
            else:
                program_body.append(code)
            
        ret_qasm = ('{};\n'
                    '{};\n'
                    '{};\n'
                    '{};'.format(
                        ';\n'.join(collected_qregs),
                        ';\n'.join(collected_cregs),
                        ';\n'.join(program_body),
                        ';\n'.join(collected_measurements)
                    ))

        return ret_qasm, collected_qregs, collected_cregs, program_body, collected_measurements
                
    @staticmethod
    def _split_outside_parens(text: str, sep: str = ",") -> list[str]:
        """Split ``text`` on ``sep`` while respecting parenthesized groups."""
        parts: list[str] = []
        buf: list[str] = []
        depth = 0
        for ch in text:
            if ch == "(":
                depth += 1
                buf.append(ch)
            elif ch == ")":
                depth -= 1
                buf.append(ch)
            elif ch == sep and depth == 0:
                parts.append("".join(buf).strip())
                buf = []
            else:
                buf.append(ch)
        tail = "".join(buf).strip()
        if tail:
            parts.append(tail)
        return parts

    @staticmethod
    def _eval_param_expr(expr: str, bindings: dict[str, str]) -> str:
        """Evaluate a QASM parameter expression with symbolic substitutions.

        ``bindings`` maps parameter names (from a gate def signature) to the
        argument expressions supplied at the call site.  Numeric constants
        ``pi`` / ``e`` are recognised; other identifiers are looked up in
        ``bindings`` and substituted as parenthesised expressions so operator
        precedence is preserved.
        """
        import math
        import re as _re

        # Substitute bound parameters first (longest names first to avoid
        # prefix collisions like ``th`` vs ``theta``).
        for name in sorted(bindings, key=len, reverse=True):
            expr = _re.sub(rf"\b{_re.escape(name)}\b", f"({bindings[name]})", expr)

        # Replace QASM constants with their Python equivalents.
        expr = _re.sub(r"\bpi\b", "math.pi", expr)
        expr = _re.sub(r"(?<![A-Za-z_])e(?![A-Za-z0-9_])", "math.e", expr)

        try:
            value = eval(expr, {"__builtins__": {}}, {"math": math})
        except Exception:
            # Could not collapse to a number (e.g. nested unbound identifier);
            # return the substituted expression so downstream parsing surfaces
            # the issue with full context.
            return expr
        return repr(float(value))

    def _expand_custom_gate_call(self, line: str, depth: int = 0) -> list[str]:
        """Expand a single program-body line into primitive lines.

        If ``line`` is a call to a user-defined gate, recursively inline its
        body with parameter / qubit-arg substitution.  Otherwise return
        ``[line]`` unchanged.  ``depth`` guards against pathological
        recursive gate definitions.
        """
        import re as _re

        if depth > 32:
            raise NotImplementedError(
                "Custom gate inlining exceeded recursion depth (32). "
                "Likely a self-referential gate definition."
            )

        gate_defs = getattr(self, "_gate_defs", {})
        if not gate_defs:
            return [line]

        # Match: name(<params>) <args>   OR   name <args>
        m = _re.match(
            r"\s*([A-Za-z_][A-Za-z0-9_]*)"
            r"(?:\s*\(([^)]*)\))?"
            r"\s+(.+)$",
            line,
        )
        if not m:
            return [line]
        name = m.group(1)
        if name not in gate_defs:
            return [line]

        param_expr_str = (m.group(2) or "").strip()
        arg_str = m.group(3).strip()

        params, qubit_args, body_lines = gate_defs[name]
        call_param_exprs = self._split_outside_parens(param_expr_str) if param_expr_str else []
        call_args = self._split_outside_parens(arg_str)

        if len(call_param_exprs) != len(params):
            raise NotImplementedError(
                f"Gate '{name}' expects {len(params)} parameters, got {len(call_param_exprs)}"
            )
        if len(call_args) != len(qubit_args):
            raise NotImplementedError(
                f"Gate '{name}' expects {len(qubit_args)} qubit arguments, got {len(call_args)}"
            )

        param_bindings = dict(zip(params, call_param_exprs))
        arg_bindings = dict(zip(qubit_args, call_args))

        expanded: list[str] = []
        for body_line in body_lines:
            new_line = body_line
            # Substitute the parameter expressions inside any (...)
            def _replace_paren(match):
                inner = match.group(1)
                expr_parts = self._split_outside_parens(inner)
                evaluated = [self._eval_param_expr(p, param_bindings) for p in expr_parts]
                return "(" + ", ".join(evaluated) + ")"
            new_line = _re.sub(r"\(([^()]*)\)", _replace_paren, new_line)

            # Substitute qubit argument identifiers (whole-word match).
            for src in sorted(arg_bindings, key=len, reverse=True):
                new_line = _re.sub(rf"\b{_re.escape(src)}\b", arg_bindings[src], new_line)

            # Recurse — body may itself reference other custom gates.
            expanded.extend(self._expand_custom_gate_call(new_line, depth=depth + 1))

        return expanded

    @staticmethod
    def _compute_id(regs, reg_name, reg_id):
        id = 0
        for stored_reg_name, stored_reg_size in regs:
            if stored_reg_name == reg_name:
                if reg_id >= stored_reg_size:
                    raise RegisterOutOfRangeError()
                return id + reg_id
            
            id += stored_reg_size
            
        raise RegisterNotFoundError()
    
    def _get_qubit_id(self, qreg_name, qreg_id):
        try:
            qubit_id = OpenQASM2_BaseParser._compute_id(self.qregs, qreg_name, qreg_id)
            return qubit_id
        except RegisterNotFoundError:
            raise RegisterNotFoundError('Cannot find qreg {}, (defined = {})'.format(
                qreg_name, self.collected_qregs_str
            ))
        except RegisterOutOfRangeError:
            raise RegisterOutOfRangeError('qreg {}[{}] out of range.)'.format(
                qreg_name, qreg_id
            ))
        
    def _get_cbit_id(self, creg_name, creg_id):
        try:
            cbit_id = OpenQASM2_BaseParser._compute_id(self.cregs, creg_name, creg_id)
            return cbit_id
        except RegisterNotFoundError:
            raise RegisterNotFoundError('Cannot find creg {}, (defined = {})'.format(
                creg_name, self.collected_cregs_str
            ))
        except RegisterOutOfRangeError:
            raise RegisterOutOfRangeError('creg {}[{}] out of range.)'.format(
                creg_name, creg_id
            ))
    
    @staticmethod
    def _check_regs(collected_regs, reg_handler):
        # check whether qregs have the same name
        names = set()
        regs = list()
        total_size = 0
        if len(collected_regs) == 0:
            raise RegisterDefinitionError("Register is empty")
        for reg_str in collected_regs:
            name, size = reg_handler(reg_str)
            if name in names:
                raise RegisterDefinitionError("Duplicate name")
            
            names.add(name)
            regs.append((name, size))
            total_size += size

        return total_size, regs
    
    def _process_measurements(self):
        for measurement in self.collected_measurements_str:
            qreg_name, qreg_id, creg_name, creg_id = OpenQASM2_LineParser.handle_measure(measurement)
            qid = self._get_qubit_id(qreg_name, qreg_id)
            cid = self._get_cbit_id(creg_name, creg_id)
            self.measure_qubits.append((qid, cid))

    def parse(self, raw_qasm):
        """Parse an OpenQASM 2.0 string and populate internal state.

        Args:
            raw_qasm: OpenQASM 2.0 string to parse.
        """
        self.raw_qasm = raw_qasm

        # format, and check if QASM code is valid
        # also return the collected statements
        (self.formatted_qasm, 
         self.collected_qregs_str, 
         self.collected_cregs_str, 
         self.program_body_str, 
         self.collected_measurements_str) = self._format_and_check()
        
        # process the total number of qubit
        try:
            self.n_qubit, self.qregs = OpenQASM2_BaseParser._check_regs(self.collected_qregs_str, OpenQASM2_LineParser.handle_qreg)
        except RegisterDefinitionError as e:
            raise RegisterDefinitionError("QReg Definition Error.\n"
                                          f"Internal error: \n{str(e)}")
        
        # process the total number of cbit
        try:
            self.n_cbit, self.cregs = OpenQASM2_BaseParser._check_regs(self.collected_cregs_str, OpenQASM2_LineParser.handle_creg)
        except RegisterDefinitionError as e:
            raise RegisterDefinitionError("CReg Definition Error.\n"
                                          f"Internal error: \n{str(e)}")
        
        # process measurements
        self._process_measurements()

        # process program body
        # Inline any user-defined-gate calls before per-line opcode lookup.
        expanded_body: list[str] = []
        for line in self.program_body_str:
            expanded_body.extend(self._expand_custom_gate_call(line))
        self.program_body_str = expanded_body

        for line in self.program_body_str:
            operation, qubits, cbits, parameters = OpenQASM2_LineParser.parse_line(line)
            if operation is None:
                continue
            
            # transform the qubit from regname+index to qubit_id
            # Note: register's validity is checked through _get_qubit_id
            if qubits:
                if isinstance(qubits, list):
                    qubits = [self._get_qubit_id(qubit[0], qubit[1]) for qubit in qubits]
                else:
                    qubits = self._get_qubit_id(qubits[0], qubits[1])

            if cbits:
                if isinstance(cbits, list):
                    cbits = [self._get_cbit_id(cbit[0], cbit[1]) for cbit in cbits]
                else:
                    cbits = self._get_cbit_id(cbits[0], cbits[1])
            
            # convert parameter to a scalar value
            if parameters and isinstance(parameters, list) and len(parameters) == 1:
                parameters = parameters[0]

            # transform into opcodes
            # opcodes = (operation,qubits,cbit,parameter,dagger_flag,control_qubits_set)
            opcode = get_opcode_from_QASM2(operation, qubits, cbits, parameters)
            
            # check if opcode is correctely converted
            if opcode is None:
                raise NotImplementedError("Opcode is not converted correctly for "
                                          f"line: {line}.\n"
                                          f"operation: {operation}"
                                          f"qubits: {qubits}"
                                          f"cbits: {cbits}"
                                          f"parameters: {parameters}"
                                          )

            self.program_body.append(opcode)
    
    def to_originir(self):
        """Convert parsed OpenQASM data to OriginIR string.

        Returns:
            str: OriginIR string representation, including any ``MEASURE``
            statements collected from the QASM source.
        """
        oir_parser = OriginIR_BaseParser()
        oir_parser.n_qubit = self.n_qubit
        oir_parser.n_cbit = self.n_cbit
        oir_parser.program_body = self.program_body
        # Without this, OriginIR output silently drops all measurements.
        oir_parser.measure_qubits = list(self.measure_qubits)

        return oir_parser.to_extended_originir()
    
    def to_circuit(self) -> Circuit:
        """
        The function coverts OpenQASM string into uniqc.Circuit object.

        In the initilization phase, we need to notice that OriginIR-based quantum circuit
        doe not need to specify how many qregs and cregs used. 
        
        Parameters:
        - qasm_str: The quantum circuit of intersts in the OpenQASM format.

        Returns:
        - origin_qcirc: The quantum circuit of intersts in the OriginIR format. 
        """
        # Create an empty Circuit object
        origincircuit = Circuit()

        # Split the QASM string into lines and parse each line
        for opcode in self.program_body:
            # unpack as 6 paramters (operation, qubits, params, cbits, dagger, control_qubits)
            origincircuit.add_gate(*opcode)

        # add measurements to the circuit, sort by cbit id
        measure_list = sorted(self.measure_qubits, key=lambda x: x[1])        

        for qubit, cbit in measure_list:
            origincircuit.measure(qubit)

        return origincircuit
