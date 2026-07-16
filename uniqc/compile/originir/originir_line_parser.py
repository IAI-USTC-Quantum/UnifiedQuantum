"""OriginIR line parser module.

This module provides regex-based parsing for individual OriginIR lines,
supporting 1-3 qubit gates, parameterized gates, dagger flags, and control qubits.

Key exports:
    OriginIR_LineParser: Parser class for individual OriginIR lines.
"""

__all__ = ["OriginIR_LineParser"]
import re


class OriginIR_LineParser:
    """Parser for individual OriginIR lines.

    Provides regex-based parsing for OriginIR gate statements with support for
    1-3 qubit gates, parameterized gates, dagger flags, and control qubits.
    """

    #: Names declared via QRAMDECL; populated at runtime by the base parser.
    _declared_qram_names: set = set()

    opname = r"([A-Za-z][A-Za-z\d]*)"
    blank = r" *"
    qid = r"q *\[ *(\d+) *\]"
    cid = r"c *\[ *(\d+) *\]"
    comma = r","
    lbracket = r"\("
    rbracket = r"\)"
    parameter = r"([-+]?\d+(\.\d*)?([eE][-+]?\d+)?)"

    # extended originir syntax
    dagger_flag = blank + "(dagger *)?"
    control_qubits = blank + (
        r"(controlled_by"
        + blank
        + lbracket
        + f"({blank}{qid}{blank}{comma})*{blank}{qid}{blank}"
        + rbracket
        + blank
        + ")?"
    )

    regexp_1q_str = "^" + opname + blank + qid + dagger_flag + control_qubits + "$"
    regexp_2q_str = "^" + opname + blank + qid + blank + comma + blank + qid + dagger_flag + control_qubits + "$"
    regexp_3q_str = (
        "^"
        + opname
        + blank
        + qid
        + blank
        + comma
        + blank
        + qid
        + blank
        + comma
        + blank
        + qid
        + dagger_flag
        + control_qubits
        + "$"
    )
    regexp_1q1p_str = (
        "^"
        + opname
        + blank
        + qid
        + blank
        + comma
        + blank
        + lbracket
        + blank
        + parameter
        + blank
        + rbracket
        + dagger_flag
        + control_qubits
        + "$"
    )
    regexp_1q2p_str = (
        "^"
        + opname
        + blank
        + qid
        + blank
        + comma
        + blank
        + lbracket
        + blank
        + parameter
        + blank
        + comma
        + blank
        + parameter
        + blank
        + rbracket
        + dagger_flag
        + control_qubits
        + "$"
    )
    regexp_1q3p_str = (
        "^"
        + opname
        + blank
        + qid
        + blank
        + comma
        + blank
        + lbracket
        + blank
        + parameter
        + blank
        + comma
        + blank
        + parameter
        + blank
        + comma
        + blank
        + parameter
        + blank
        + rbracket
        + dagger_flag
        + control_qubits
        + "$"
    )
    regexp_1q4p_str = (
        "^"
        + opname
        + blank
        + qid
        + blank
        + comma
        + blank
        + lbracket
        + blank
        + parameter
        + blank
        + comma
        + blank
        + parameter
        + blank
        + comma
        + blank
        + parameter
        + blank
        + comma
        + blank
        + parameter
        + blank
        + rbracket
        + dagger_flag
        + control_qubits
        + "$"
    )
    regexp_2q1p_str = (
        "^"
        + opname
        + blank
        + qid
        + blank
        + comma
        + blank
        + qid
        + blank
        + comma
        + blank
        + lbracket
        + blank
        + parameter
        + blank
        + rbracket
        + dagger_flag
        + control_qubits
        + "$"
    )

    regexp_2q3p_str = (
        "^"
        + opname
        + blank
        + qid
        + blank
        + comma
        + blank
        + qid
        + blank
        + comma
        + blank
        + lbracket
        + blank
        + parameter
        + blank  # 1
        + comma
        + blank
        + parameter
        + blank  # 2
        + comma
        + blank
        + parameter
        + blank  # 3
        + rbracket
        + dagger_flag
        + control_qubits
        + "$"
    )

    regexp_2q15p_str = (
        "^"
        + opname
        + blank
        + qid
        + blank
        + comma
        + blank
        + qid
        + blank
        + comma
        + blank
        + lbracket
        + blank
        + parameter
        + blank  # 1
        + comma
        + blank
        + parameter
        + blank  # 1
        + comma
        + blank
        + parameter
        + blank  # 3
        + comma
        + blank
        + parameter
        + blank  # 4
        + comma
        + blank
        + parameter
        + blank  # 5
        + comma
        + blank
        + parameter
        + blank  # 6
        + comma
        + blank
        + parameter
        + blank  # 7
        + comma
        + blank
        + parameter
        + blank  # 8
        + comma
        + blank
        + parameter
        + blank  # 9
        + comma
        + blank
        + parameter
        + blank  # 10
        + comma
        + blank
        + parameter
        + blank  # 11
        + comma
        + blank
        + parameter
        + blank  # 12
        + comma
        + blank
        + parameter
        + blank  # 13
        + comma
        + blank
        + parameter
        + blank  # 14
        + comma
        + blank
        + parameter
        + blank  # 15
        + rbracket
        + dagger_flag
        + control_qubits
        + "$"
    )

    regexp_measure_str = "^" + r"MEASURE" + blank + qid + blank + comma + blank + cid + "$"
    regexp_barrier_str = r"^BARRIER" + f"(({blank}{qid}{blank}{comma})*{blank}{qid}{blank})" + "$"
    regexp_control_str = r"^(CONTROL|ENDCONTROL)" + f"(({blank}{qid}{blank}{comma})*{blank}{qid}{blank})" + "$"

    # DEF block header (OriginIR-ext) — reuses the named-register declaration
    # syntax for the qubit signature:
    #   DEF name(q[2], anc[1]) (theta1, theta2)
    # The first parenthesised group is a comma-separated list of ``name[size]``
    # register declarations; the optional trailing group is a comma-separated
    # list of scalar parameter names.
    reg_ident = r"[A-Za-z_][A-Za-z0-9_]*"
    regexp_def_str = (
        "^DEF"
        + blank
        + rf"({reg_ident})"  # 1: circuit name
        + blank
        + r"\("
        + blank
        + r"([^()]*?)"  # 2: register-declaration list
        + blank
        + r"\)"
        + "(?:"
        + blank
        + r"\("
        + blank
        + r"([^()]*?)"  # 3: scalar parameter-name list
        + blank
        + r"\)"
        + ")?"
        + blank
        + "$"
    )
    regexp_enddef_str = "^ENDDEF$"

    # DEF subroutine call: name(<qubit args>) [(<scalar param args>)]
    #   bell(q[0], q[1])   |   rx_gate(q[3]) (1.57)   |   bell(a)
    regexp_defcall_str = (
        "^"
        + rf"({reg_ident})"  # 1: subroutine name
        + blank
        + r"\("
        + r"([^()]*)"  # 2: qubit args
        + r"\)"
        + "(?:"
        + blank
        + r"\("
        + r"([^()]*)"  # 3: scalar param args
        + r"\)"
        + ")?"
        + blank
        + "$"
    )

    # QRAMDECL name addr_size,data_size
    regexp_qramdecl_str = (
        r"^QRAMDECL" + blank + r"([A-Za-z_][A-Za-z0-9_]*)" + blank + r"(\d+)\s*,\s*(\d+)" + blank + "$"
    )

    regexp_1q = re.compile(regexp_1q_str)
    regexp_2q = re.compile(regexp_2q_str)
    regexp_3q = re.compile(regexp_3q_str)
    regexp_1q1p = re.compile(regexp_1q1p_str)
    regexp_1q2p = re.compile(regexp_1q2p_str)
    regexp_1q3p = re.compile(regexp_1q3p_str)
    regexp_1q4p = re.compile(regexp_1q4p_str)
    regexp_2q1p = re.compile(regexp_2q1p_str)
    regexp_2q3p = re.compile(regexp_2q3p_str)
    regexp_2q15p = re.compile(regexp_2q15p_str)
    regexp_meas = re.compile(regexp_measure_str)
    regexp_barrier = re.compile(regexp_barrier_str)
    regexp_control = re.compile(regexp_control_str)
    regexp_def = re.compile(regexp_def_str)
    regexp_enddef = re.compile(regexp_enddef_str)
    regexp_defcall = re.compile(regexp_defcall_str)
    regexp_qramdecl = re.compile(regexp_qramdecl_str)
    regexp_qid = re.compile(qid)

    def __init__(self):
        pass

    @staticmethod
    def handle_1q(line):
        """Parse a 1-qubit gate line.

        Returns:
            tuple: (operation, qubit, dagger_flag, control_qubits)
        """
        matches = OriginIR_LineParser.regexp_1q.match(line)
        operation = matches.group(1)
        q = int(matches.group(2))
        dagger_flag = True if matches.group(3) is not None else False
        control_qubits = []
        if matches.group(4) is not None:
            control_qubits = [int(q) for q in OriginIR_LineParser.regexp_qid.findall(matches.group(4))]

        return operation, q, dagger_flag, control_qubits

    @staticmethod
    def handle_2q(line):
        """Parse a 2-qubit gate line.

        Returns:
            tuple: (operation, [q1, q2], dagger_flag, control_qubits)
        """
        matches = OriginIR_LineParser.regexp_2q.match(line)
        operation = matches.group(1)
        if operation.lower() == "ecr":
            operation = "ECR"
        q1 = int(matches.group(2))
        q2 = int(matches.group(3))
        dagger_flag = True if matches.group(4) is not None else False
        control_qubits = []
        if matches.group(5) is not None:
            control_qubits = [int(q) for q in OriginIR_LineParser.regexp_qid.findall(matches.group(5))]

        return operation, [q1, q2], dagger_flag, control_qubits

    @staticmethod
    def handle_3q(line):
        """Parse a 3-qubit gate line.

        Returns:
            tuple: (operation, [q1, q2, q3], dagger_flag, control_qubits)
        """
        matches = OriginIR_LineParser.regexp_3q.match(line)
        operation = matches.group(1)
        q1 = int(matches.group(2))
        q2 = int(matches.group(3))
        q3 = int(matches.group(4))
        dagger_flag = True if matches.group(5) is not None else False
        control_qubits = []
        if matches.group(6) is not None:
            control_qubits = [int(q) for q in OriginIR_LineParser.regexp_qid.findall(matches.group(6))]

        return operation, [q1, q2, q3], dagger_flag, control_qubits

    @staticmethod
    def handle_1q1p(line):
        """Parse a 1-qubit 1-parameter gate line.

        Returns:
            tuple: (operation, qubit, parameter, dagger_flag, control_qubits)
        """
        matches = OriginIR_LineParser.regexp_1q1p.match(line)
        operation = matches.group(1)
        q = int(matches.group(2))
        parameter = float(matches.group(3))
        dagger_flag = True if matches.group(6) is not None else False
        control_qubits = []
        if matches.group(7) is not None:
            control_qubits = [int(q) for q in OriginIR_LineParser.regexp_qid.findall(matches.group(7))]

        return operation, q, parameter, dagger_flag, control_qubits

    @staticmethod
    def handle_1q2p(line):
        """Parse a 1-qubit 2-parameter gate line.

        Returns:
            tuple: (operation, qubit, [p1, p2], dagger_flag, control_qubits)
        """
        matches = OriginIR_LineParser.regexp_1q2p.match(line)
        operation = matches.group(1)
        q = int(matches.group(2))
        parameter1 = float(matches.group(3))
        parameter2 = float(matches.group(6))
        dagger_flag = True if matches.group(9) is not None else False
        control_qubits = []
        if matches.group(10) is not None:
            control_qubits = [int(q) for q in OriginIR_LineParser.regexp_qid.findall(matches.group(10))]

        return operation, q, [parameter1, parameter2], dagger_flag, control_qubits

    @staticmethod
    def handle_1q3p(line):
        """Parse a 1-qubit 3-parameter gate line.

        Returns:
            tuple: (operation, qubit, [p1, p2, p3], dagger_flag, control_qubits)
        """
        matches = OriginIR_LineParser.regexp_1q3p.match(line)
        operation = matches.group(1)
        q = int(matches.group(2))
        parameter1 = float(matches.group(3))
        parameter2 = float(matches.group(6))
        parameter3 = float(matches.group(9))
        dagger_flag = True if matches.group(12) is not None else False
        control_qubits = []
        if matches.group(13) is not None:
            control_qubits = [int(q) for q in OriginIR_LineParser.regexp_qid.findall(matches.group(13))]

        return operation, q, [parameter1, parameter2, parameter3], dagger_flag, control_qubits

    @staticmethod
    def handle_1q4p(line):
        """Parse a 1-qubit 4-parameter gate line.

        Returns:
            tuple: (operation, qubit, [p1, p2, p3, p4], dagger_flag, control_qubits)
        """
        matches = OriginIR_LineParser.regexp_1q4p.match(line)
        operation = matches.group(1)
        q = int(matches.group(2))
        parameter1 = float(matches.group(3))
        parameter2 = float(matches.group(6))
        parameter3 = float(matches.group(9))
        parameter4 = float(matches.group(12))
        dagger_flag = True if matches.group(15) is not None else False
        control_qubits = []
        if matches.group(16) is not None:
            control_qubits = [int(q) for q in OriginIR_LineParser.regexp_qid.findall(matches.group(16))]

        return operation, q, [parameter1, parameter2, parameter3, parameter4], dagger_flag, control_qubits

    @staticmethod
    def handle_2q1p(line):
        """Parse a 2-qubit 1-parameter gate line.

        Returns:
            tuple: (operation, [q1, q2], parameter, dagger_flag, control_qubits)
        """
        matches = OriginIR_LineParser.regexp_2q1p.match(line)
        operation = matches.group(1)
        q1 = int(matches.group(2))
        q2 = int(matches.group(3))
        parameter1 = float(matches.group(4))
        dagger_flag = True if matches.group(7) is not None else False
        control_qubits = []
        if matches.group(8) is not None:
            control_qubits = [int(q) for q in OriginIR_LineParser.regexp_qid.findall(matches.group(8))]

        return operation, [q1, q2], parameter1, dagger_flag, control_qubits

    @staticmethod
    def handle_2q3p(line):
        """Parse a 2-qubit 3-parameter gate line.

        Returns:
            tuple: (operation, [q1, q2], [p1, p2, p3], dagger_flag, control_qubits)
        """
        matches = OriginIR_LineParser.regexp_2q3p.match(line)
        operation = matches.group(1)
        q1 = int(matches.group(2))
        q2 = int(matches.group(3))
        parameter1 = float(matches.group(4))
        parameter2 = float(matches.group(7))
        parameter3 = float(matches.group(10))
        dagger_flag = True if matches.group(13) is not None else False
        control_qubits = []
        if matches.group(14) is not None:
            control_qubits = [int(q) for q in OriginIR_LineParser.regexp_qid.findall(matches.group(14))]

        return operation, [q1, q2], [parameter1, parameter2, parameter3], dagger_flag, control_qubits

    @staticmethod
    def handle_2q15p(line):
        """Parse a 2-qubit 15-parameter gate line.

        Returns:
            tuple: (operation, [q1, q2], parameters, dagger_flag, control_qubits)
        """
        matches = OriginIR_LineParser.regexp_2q15p.match(line)
        operation = matches.group(1)
        q1 = int(matches.group(2))
        q2 = int(matches.group(3))
        parameters = []
        for i in range(15):
            parameters.append(float(matches.group(4 + i * 3)))

        dagger_flag = True if matches.group(49) is not None else False
        control_qubits = []
        if matches.group(50) is not None:
            control_qubits = [int(q) for q in OriginIR_LineParser.regexp_qid.findall(matches.group(50))]

        return operation, [q1, q2], parameters, dagger_flag, control_qubits

    @staticmethod
    def handle_measure(line):
        """Parse a MEASURE statement line.

        Returns:
            tuple: (qubit, cbit)
        """
        matches = OriginIR_LineParser.regexp_meas.match(line)
        q = int(matches.group(1))
        c = int(matches.group(2))
        return q, c

    @staticmethod
    def handle_barrier(line):
        """Parse a BARRIER statement line.

        Returns:
            tuple: ("BARRIER", qubit_indices)
        """
        matches = OriginIR_LineParser.regexp_barrier.match(line)
        # Extract individual qubit patterns
        qubits = OriginIR_LineParser.regexp_qid.findall(line)
        # Extract only the numeric part of each qubit pattern
        qubit_indices = [int(q) for q in qubits]
        return "BARRIER", qubit_indices

    @staticmethod
    def handle_control(line):
        """
        Parse a line to extract control qubits information and the type of control operation.

        This function analyzes a given line of text to identify and extract information about
        control qubits and determine whether the line represents the beginning of a control operation
        (CONTROL) or the end of a control operation (ENDCONTROL) in OriginIR language.

        Parameters
        ----------
        line : str
            The line of text to be parsed for control qubit information.

        Returns
        -------
        tuple of (str, list)
            A tuple where the first element is a string indicating the control operation type
            ("CONTROL" or "ENDCONTROL") and the second element is a list of integers representing
            the parsed control qubits.

        Notes
        -----
        The function relies on the `regexp_control` regular expression to match the CONTROL or
        ENDCONTROL patterns in OriginIR language. This regular expression should be predefined
        and properly constructed to capture the necessary information from the line.
        """
        matches = OriginIR_LineParser.regexp_control.match(line)
        # Extracting the operation type and multiple control qubits
        operation_type = matches.group(1)
        qubits = OriginIR_LineParser.regexp_qid.findall(matches.group(2))
        controls = [int(ctrl) for ctrl in qubits]
        return operation_type, controls

    @staticmethod
    def handle_dagger(line):
        """
        Parse a line to identify DAGGER or ENDDAGGER commands in OriginIR.

        This function checks a line of text to determine if it contains a command
        related to the start or end of a DAGGER operation block in the OriginIR language.

        Parameters
        ----------
        line : str
            The line of text to be parsed.

        Returns
        -------
        str or None
            Returns "DAGGER" if the line is a DAGGER command, "ENDDAGGER" if it's an ENDDAGGER command,
            or None if neither command is present.

        Notes
        -----
        The DAGGER command in OriginIR denotes the start of a block where the operations are to be
        applied in reverse order with conjugate transposition (dagger operation). The ENDDAGGER command
        signifies the end of such a block.
        """
        if "ENDDAGGER" in line:
            return "ENDDAGGER"
        elif "DAGGER" in line:
            return "DAGGER"
        else:
            return None

    @staticmethod
    def handle_def(line):
        """Parse a DEF block header line.

        Format: ``DEF name(reg[size], ...) (param1, param2, ...)``.

        The qubit signature reuses the named-register declaration syntax: a
        comma-separated list of ``name[size]`` register declarations. The
        optional trailing parenthesised group is a comma-separated list of
        **scalar** parameter names.

        Returns:
            tuple: ``(operation="DEF", formal_qregs, params, name)`` where
                ``formal_qregs`` is a list of ``(reg_name, size)`` tuples (in
                declaration order) and ``params`` is a list of scalar
                parameter-name strings.
        """
        matches = OriginIR_LineParser.regexp_def.match(line.strip())
        if not matches:
            raise ValueError(f"Invalid DEF line: {line}")

        name = matches.group(1)

        # First parenthesised group: named-register declarations name[size].
        reg_group = matches.group(2) or ""
        formal_qregs = [
            (reg_name, int(size))
            for reg_name, size in re.findall(r"([A-Za-z_][A-Za-z0-9_]*) *\[ *(\d+) *\]", reg_group)
        ]
        if not formal_qregs:
            raise ValueError(f"DEF header must declare at least one register (e.g. 'q[2]'): {line}")

        # Second parenthesised group (optional): scalar parameter names.
        param_group = matches.group(3)
        params: list[str] = []
        if param_group is not None:
            params = [p.strip() for p in param_group.split(",") if p.strip()]

        return ("DEF", formal_qregs, params, name)

    @staticmethod
    def handle_def_call(line):
        """Parse a DEF subroutine call line.

        Format: ``name(<qubit args>) [(<scalar param args>)]`` where the qubit
        args are a comma-separated list of qubit references (``reg[idx]`` or a
        whole register name ``reg``) and the optional trailing group is a
        comma-separated list of scalar parameter values.

        Returns:
            tuple: ``(name, qubit_args_str, param_args_str_or_None)`` — the two
                argument groups are returned verbatim for the base parser to
                resolve against the active register maps.
        """
        matches = OriginIR_LineParser.regexp_defcall.match(line.strip())
        if not matches:
            raise ValueError(f"Invalid DEF call line: {line}")
        return matches.group(1), matches.group(2), matches.group(3)

    @staticmethod
    def handle_qramdecl(line):
        """Parse a QRAMDECL statement.

        Format: QRAMDECL name addr_size,data_size

        Returns:
            tuple: ("QRAMDECL", name, addr_size, data_size)
        """
        matches = OriginIR_LineParser.regexp_qramdecl.match(line.strip())
        if not matches:
            raise ValueError(f"Invalid QRAMDECL line: {line}")
        name = matches.group(1)
        addr_size = int(matches.group(2))
        data_size = int(matches.group(3))
        return "QRAMDECL", name, addr_size, data_size

    @staticmethod
    def handle_qram_call(line, qram_name):
        """Parse a QRAM call line: ``name q[..], q[..], ... [dagger] [controlled_by(...)]``.

        The address/data qubit list uses the same variable-length syntax as
        BARRIER. The optional inline ``dagger`` keyword and
        ``controlled_by(...)`` clause (extended-syntax suffixes shared with
        ordinary gates) are parsed independently of the qubit list so that
        controlled QRAM round-trips through OriginIR-ext text. QRAM XOR-loads
        are self-inverse, so ``dagger`` is accepted for symmetry but does not
        change execution semantics.

        Returns:
            tuple: (qram_name, qubit_indices, dagger_flag, control_qubits)
        """
        # Strip the leading operation name, then split off any
        # `controlled_by(...)` clause before scanning for qubit indices —
        # otherwise q[..] references inside the controlled_by(...) clause
        # would be mistaken for address/data qubits.
        remainder = line[len(qram_name) :]
        before_control, sep, control_clause = remainder.partition("controlled_by")
        dagger_flag = bool(re.search(r"\bdagger\b", before_control))
        before_control = re.sub(r"\bdagger\b", "", before_control)
        qubit_indices = [int(q) for q in OriginIR_LineParser.regexp_qid.findall(before_control)]
        control_qubits = [int(q) for q in OriginIR_LineParser.regexp_qid.findall(control_clause)] if sep else []
        return qram_name, qubit_indices, dagger_flag, control_qubits

    @staticmethod
    def parse_line(line):
        """Parse a single OriginIR line and return operation details.

        Args:
            line: Single line of OriginIR code.

        Returns:
            tuple: (operation, qubits, cbit, parameter, dagger_flag, control_qubits)
        """

        try:
            q = None
            c = None
            operation = None
            parameter = None
            dagger_flag = None
            control_qubits = None

            # remove the empty line
            if not line:
                return q, c, operation, parameter, dagger_flag, control_qubits

            line = line.strip()
            # extract operation
            operation = line.split()[0]
            # Normalise ECR to uppercase (case-insensitive support)
            if operation.lower() == "ecr":
                operation = "ECR"

            if operation == "QINIT":
                q = int(line.strip().split()[1])
                operation = "QINIT"
            elif operation == "CREG":
                c = int(line.strip().split()[1])
                operation = "CREG"
            # 1-qubit gates
            elif (
                operation == "H"
                or operation == "X"
                or operation == "Y"
                or operation == "Z"
                or operation == "S"
                or operation == "SX"
                or operation == "T"
                or operation == "I"
            ):
                operation, q, dagger_flag, control_qubits = OriginIR_LineParser.handle_1q(line)
            # 2-qubit gates
            elif (
                operation == "CZ"
                or operation == "CNOT"
                or operation == "ECR"
                or operation == "SWAP"
                or operation == "ISWAP"
            ):
                operation, q, dagger_flag, control_qubits = OriginIR_LineParser.handle_2q(line)
            # 3-qubit gates
            elif operation == "TOFFOLI" or operation == "CSWAP":
                operation, q, dagger_flag, control_qubits = OriginIR_LineParser.handle_3q(line)
            # 1q1p gates
            elif (
                operation == "RX"
                or operation == "RY"
                or operation == "RZ"
                or operation == "U1"
                or operation == "RPhi90"
                or operation == "RPhi180"
                or operation == "Depolarizing"
                or operation == "BitFlip"
                or operation == "AmplitudeDamping"
                or operation == "PhaseFlip"
            ):
                operation, q, parameter, dagger_flag, control_qubits = OriginIR_LineParser.handle_1q1p(line)
            # 1q2p gates
            elif operation == "RPhi" or operation == "U2":
                operation, q, parameter, dagger_flag, control_qubits = OriginIR_LineParser.handle_1q2p(line)
            # 1q3p gates
            elif operation == "U3" or operation == "PauliError1Q":
                operation, q, parameter, dagger_flag, control_qubits = OriginIR_LineParser.handle_1q3p(line)
            # 2q1p gates
            elif (
                operation == "XX"
                or operation == "YY"
                or operation == "ZZ"
                or operation == "XY"
                or operation == "TwoQubitDepolarizing"
            ):
                operation, q, parameter, dagger_flag, control_qubits = OriginIR_LineParser.handle_2q1p(line)
            # 2q3p gates
            elif operation == "PHASE2Q":
                operation, q, parameter, dagger_flag, control_qubits = OriginIR_LineParser.handle_2q3p(line)
            # 2q15p gates
            elif operation == "UU15" or operation == "PauliError2Q":
                operation, q, parameter, dagger_flag, control_qubits = OriginIR_LineParser.handle_2q15p(line)
            elif operation == "BARRIER":
                operation = "BARRIER"
                operation, q = OriginIR_LineParser.handle_barrier(line)
                dagger_flag = False
                control_qubits = []
            elif operation == "MEASURE":
                operation = "MEASURE"
                q, c = OriginIR_LineParser.handle_measure(line)
            elif operation == "CONTROL":
                operation, q = OriginIR_LineParser.handle_control(line)
            elif operation == "ENDCONTROL":
                operation = "ENDCONTROL"
            elif operation == "DAGGER" or operation == "ENDDAGGER":
                operation = OriginIR_LineParser.handle_dagger(line)
            elif operation == "DEF":
                # Structural DEF header. The full block (body + ENDDEF) and any
                # subroutine calls are expanded by OriginIR_BaseParser; here we
                # only return the header in the standard 6-tuple shape so
                # line-level consumers can recognise (and skip) it.
                _, formal_qregs, params, _name = OriginIR_LineParser.handle_def(line)
                q = formal_qregs
                parameter = params
                dagger_flag = False
                control_qubits = []
            elif operation == "ENDDEF":
                operation = "ENDDEF"
                dagger_flag = False
                control_qubits = []
            elif operation == "QRAMDECL":
                operation, name, addr_size, data_size = OriginIR_LineParser.handle_qramdecl(line)
                q = (name, addr_size, data_size)
                dagger_flag = False
                control_qubits = []
            elif operation in OriginIR_LineParser._declared_qram_names:
                # QRAM call — same qubit-list syntax as BARRIER, plus inline
                # dagger / controlled_by(...) extended-syntax suffixes.
                operation, q, dagger_flag, control_qubits = OriginIR_LineParser.handle_qram_call(line, operation)
            else:
                # print("something wrong")
                raise NotImplementedError(f"A invalid line: {line}.")

            return operation, q, c, parameter, dagger_flag, control_qubits
        except AttributeError as e:
            raise RuntimeError(f"Error when parsing the line: {line}") from e


if __name__ == "__main__":
    print(OriginIR_LineParser.regexp_1q_str)
    matches = OriginIR_LineParser.regexp_1q.match("H  q [ 45 ]")
    print(matches.group(0))
    print(matches.group(1))  # H
    print(matches.group(2))  # 45

    print(OriginIR_LineParser.regexp_1q_str)
    matches = OriginIR_LineParser.regexp_1q.match("H  q [ 45 ] dagger   controlled_by (q[0], q[1], q[2])")
    print(matches.group(0))
    print(matches.group(1))  # H
    print(matches.group(2))  # 45
    print(matches.group(3))  # dagger
    print(matches.group(4))  # controlled_by (q[0], q[1], q[2])
    print(OriginIR_LineParser.regexp_1q1p_str)

    matches = OriginIR_LineParser.regexp_1q1p.match("RX  q [ 45 ] , ( 1.1e+3) dagger")
    print(matches.group(0))
    print(matches.group(1))  # RX
    print(matches.group(2))  # 45
    print(matches.group(3))  # 1.1e+3
    print(matches.group(4))  #
    print(matches.group(5))  #
    print(matches.group(6))  # dagger
    print(matches.group(7))  # None

    print(OriginIR_LineParser.regexp_1q2p_str)
    matches = OriginIR_LineParser.regexp_1q2p.match("Rphi q[ 45 ], ( -1.1 , 1.2e-5) dagger")
    print(matches.group(0))
    print(matches.group(1))  # Rphi
    print(matches.group(2))  # 45
    print(matches.group(3))  # -1.1
    print(matches.group(4))  #
    print(matches.group(5))  #
    print(matches.group(6))  # 1.2e-5
    print(matches.group(7))  #
    print(matches.group(8))  #
    print(matches.group(9))  # dagger

    print(OriginIR_LineParser.regexp_1q3p_str)
    matches = OriginIR_LineParser.regexp_1q3p.match("U3 q[ 45 ], ( -1.1 , 1.2e-5 , 0.11) dagger")
    print(matches.group(0))
    print(matches.group(1))  # U3
    print(matches.group(2))  # 45
    print(matches.group(3))  # -1.1
    print(matches.group(4))  #
    print(matches.group(5))  #
    print(matches.group(6))  # 1.2e-5
    print(matches.group(7))  #
    print(matches.group(8))  #
    print(matches.group(9))  # 0.11
    print(matches.group(10))  #
    print(matches.group(11))  #
    print(matches.group(12))  # dagger

    print(OriginIR_LineParser.regexp_1q4p_str)
    matches = OriginIR_LineParser.regexp_1q4p.match("U4 q[ 45 ], ( -1.1 , 1.2e-5, 0 , 0.11)   dagger")
    print(matches.group(0))
    print(matches.group(1))  # U4
    print(matches.group(2))  # 45
    print(matches.group(3))  # -1.1
    print(matches.group(4))  #
    print(matches.group(5))  #
    print(matches.group(6))  # 1.2e-5
    print(matches.group(7))  #
    print(matches.group(8))  #
    print(matches.group(9))  # 0
    print(matches.group(10))  #
    print(matches.group(11))  #
    print(matches.group(12))  # 0.11
    print(matches.group(13))  #
    print(matches.group(14))  #
    print(matches.group(15))  # dagger

    print(OriginIR_LineParser.regexp_2q_str)
    matches = OriginIR_LineParser.regexp_2q.match("CNOT q[ 45], q[46 ]")
    print(matches.group(0))
    print(matches.group(1))  # CNOT
    print(matches.group(2))  # 45
    print(matches.group(3))  # 46

    print(OriginIR_LineParser.regexp_3q_str)
    matches = OriginIR_LineParser.regexp_3q.match("TOFFOLI q[ 45], q[46 ], q [ 42 ]")
    print(matches.group(0))
    print(matches.group(1))  # TOFFOLI
    print(matches.group(2))  # 45
    print(matches.group(3))  # 46
    print(matches.group(4))  # 42

    print(OriginIR_LineParser.regexp_2q1p_str)
    matches = OriginIR_LineParser.regexp_2q1p.match("XY q[ 45], q[46 ], ( -1.1 )  dagger")
    print(matches.group(0))
    print(matches.group(1))  # XY
    print(matches.group(2))  # 45
    print(matches.group(3))  # 46
    print(matches.group(4))  # -1.1
    print(matches.group(5))  #
    print(matches.group(6))  #
    print(matches.group(7))  # dagger

    print(OriginIR_LineParser.regexp_2q3p_str)
    matches = OriginIR_LineParser.regexp_2q3p.match(
        "PHASE2Q q[ 45], q[46 ], ( -1.1, 1.5, 8 ) controlled_by (q[0], q[1], q[2])"
    )
    print(matches.group(0))
    print(matches.group(1))  # XY
    print(matches.group(2))  # 45
    print(matches.group(3))  # 46
    print(matches.group(4))  # -1.1
    print(matches.group(5))
    print(matches.group(6))
    print(matches.group(7))  # 1.5
    print(matches.group(8))
    print(matches.group(9))
    print(matches.group(10))  # 8
    print(matches.group(11))  #
    print(matches.group(12))  #
    print(matches.group(13))  # dagger (None)
    print(matches.group(14))  # controlled_by (q[0], q[1], q[2])

    print(OriginIR_LineParser.regexp_2q15p_str)
    matches = OriginIR_LineParser.regexp_2q15p.match(
        "UU15 q[ 45], q[46 ], ( 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15 ) dagger"
    )
    print(matches.group(0))
    print(matches.group(1))  # UU15
    print(matches.group(2))  # 45
    print(matches.group(3))  # 46
    print(matches.group(4))  # 1
    print(matches.group(7))  # 2
    print(matches.group(10))  # 3
    print(matches.group(13))  # 4
    print(matches.group(16))  # 5
    print(matches.group(19))  # 6
    print(matches.group(22))  # 7
    print(matches.group(25))  # 8
    print(matches.group(28))  # 9
    print(matches.group(31))  # 10
    print(matches.group(34))  # 11
    print(matches.group(37))  # 12
    print(matches.group(40))  # 13
    print(matches.group(43))  # 14
    print(matches.group(46))  # 15
    print(matches.group(49))  # dagger
    print(matches.group(50))  # None

    print(OriginIR_LineParser.regexp_measure_str)
    matches = OriginIR_LineParser.regexp_meas.match("MEASURE  q [ 45 ] ,  c[ 11 ]")
    print(matches.group(0))
    print(matches.group(1))  # 45
    print(matches.group(2))  # 11

    print(OriginIR_LineParser.regexp_control_str)
    matches = OriginIR_LineParser.regexp_control.match("CONTROL   q [ 45] , q[ 46]  ,  q [  999 ]")
    print(matches.group(0))
    print(matches.group(1))  # CONTROL
    print(matches.group(2))  #    q [ 45] , q[ 46]  ,  q [  999 ]
    all_matches = OriginIR_LineParser.regexp_qid.findall(matches.group(2))
    print(all_matches)  # ['45', '46', '999']
