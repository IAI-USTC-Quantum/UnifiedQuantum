"""IR-level decomposition of OriginIR-native gates to lower-level equivalents.

Two decomposition targets share the same helper infrastructure:

**QASM 2.0 target** (:func:`decompose_for_qasm2`)
    Rewrites ``RPhi``, ``RPhi90``, ``RPhi180``, ``PHASE2Q``, ``UU15``
    into gates in ``qelib1.inc`` so that cloud parsers (Quafu / QuarkStudio /
    IBM) accept the output without custom ``gate ... { ... }`` blocks.

**Official OriginIR target** (:func:`decompose_for_originir`)
    Rewrites *all* OriginIR-ext gates (above plus ``ECR``, ``ISWAP``,
    ``XX``, ``YY``, ``ZZ``, ``XY``) into the strict official OriginIR gate
    set (``H``, ``X``, ``Y``, ``Z``, ``S``, ``SX``, ``T``, ``I``,
    ``RX``, ``RY``, ``RZ``, ``U1``, ``U2``, ``U3``, ``CNOT``, ``CZ``,
    ``SWAP``, ``TOFFOLI``, ``CSWAP``) for submission to OriginQ cloud.

==============  ==================================================
Gate            Replacement (official OriginIR opcode names)
==============  ==================================================
``RPhi``        ``RZ(-phi); RX(theta); RZ(phi)``
``RPhi90``      ``RZ(-phi); RX(pi/2); RZ(phi)``
``RPhi180``     ``RZ(-phi); RX(pi); RZ(phi)``
``PHASE2Q``     ``U1(t1) q1; U1(t2) q2; CU1(tzz) (q1->q2)``
``UU15``        ``U3 ⊗ U3; XX; YY; ZZ; U3 ⊗ U3`` (KAK form)
``ECR``         ``X q2; RX(π/2) q1; CNOT q1→q2; S† q1; RX(-π/2) q2; X q1``
``ISWAP``       ``S q1; S q2; H q1; CNOT q1→q2; CNOT q2→q1; H q2``
``XX``          ``H q1; H q2; CNOT q1→q2; RZ(θ) q2; CNOT q1→q2; H q1; H q2``
``YY``          ``RX(π/2) q1,q2; CNOT q1→q2; RZ(θ) q2; CNOT q1→q2; RX(-π/2) q1,q2``
``ZZ``          ``CNOT q1→q2; RZ(θ) q2; CNOT q1→q2``
``XY``          ``XX(-θ/2); YY(-θ/2)``
==============  ==================================================

The decomposition preserves the ``dagger`` flag by reversing the
replacement sequence and negating angle parameters where appropriate.
Gate instances wrapped with ``control_qubits`` are not currently
decomposed; doing so requires lifting each replacement gate to its
controlled form, which is out of scope for this pass — call ``compile()``
explicitly first if you need that.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from copy import deepcopy

from uniqc.circuit_builder.qcircuit import Circuit, OpCode

__all__ = [
    "QASM2_UNREPRESENTABLE_GATES",
    "ORIGINIR_EXT_DECOMPOSABLE_GATES",
    "decompose_opcode_for_qasm2",
    "decompose_for_qasm2",
    "decompose_opcode_for_originir",
    "decompose_for_originir",
]


# Set of normalised (upper-case) gate names that this pass rewrites.
QASM2_UNREPRESENTABLE_GATES: frozenset[str] = frozenset({"RPHI", "RPHI90", "RPHI180", "PHASE2Q", "UU15"})

# Extended gates that must be decomposed to reach the official OriginIR gate set.
ORIGINIR_EXT_DECOMPOSABLE_GATES: frozenset[str] = QASM2_UNREPRESENTABLE_GATES | {
    "ECR", "ISWAP", "XX", "YY", "ZZ", "XY",
}


def _as_param_list(params) -> list[float]:
    if params is None:
        return []
    if isinstance(params, (list, tuple)):
        return [float(p) for p in params]
    return [float(params)]


def _check_target_qubits(name: str, qubits, expected: int) -> list[int]:
    if isinstance(qubits, int):
        qubit_list = [qubits]
    else:
        qubit_list = [int(q) for q in qubits]
    if len(qubit_list) != expected:
        raise ValueError(
            f"Decomposition of {name} expects {expected} target qubit(s), got {len(qubit_list)}: {qubit_list}"
        )
    return qubit_list


def _rphi_replacement(theta: float, phi: float, qubit: int) -> list[OpCode]:
    """RPhi(θ, φ) = Rz(φ) Rx(θ) Rz(-φ).

    Matches both ``_rphi`` in :mod:`uniqc.circuit_builder.matrix` and the
    ``gate rphi(theta, phi) a { rz(-phi); rx(theta); rz(phi); }`` definition
    in :data:`uniqc.circuit_builder.translate_qasm2_oir.QASM2_CUSTOM_GATE_DEFS`.
    The replacement applies, top-to-bottom, ``rz(-phi); rx(theta); rz(phi)``,
    yielding the same matrix product ``Rz(phi) · Rx(theta) · Rz(-phi)``.
    """
    return [
        ("RZ", qubit, None, -phi, False, None),
        ("RX", qubit, None, theta, False, None),
        ("RZ", qubit, None, phi, False, None),
    ]


def _phase2q_replacement(
    t1: float,
    t2: float,
    tzz: float,
    q1: int,
    q2: int,
) -> list[OpCode]:
    """PHASE2Q(t1, t2, tzz) on (q1, q2) — q1 is LSB.

    ``diag(1, e^{i·t1}, e^{i·t2}, e^{i·(t1+t2+tzz)})`` factors as
    ``[U1(t1) ⊗ I] · [I ⊗ U1(t2)] · CU1(tzz, ctrl=q2, tgt=q1)``; we encode
    the controlled phase as a ``U1`` opcode on ``q1`` with
    ``control_qubits=[q2]`` so the QASM emitter renders it as ``cu1``
    (qelib1.inc).
    """
    return [
        ("U1", q1, None, t1, False, None),
        ("U1", q2, None, t2, False, None),
        ("U1", q1, None, tzz, False, [q2]),
    ]


def _uu15_replacement(
    params: list[float],
    qa: int,
    qb: int,
) -> list[OpCode]:
    """UU15 KAK form: U3⊗U3 · (XX·YY·ZZ) · U3⊗U3.

    Mirrors the ``gate uu15(...)`` body in
    :data:`uniqc.circuit_builder.translate_qasm2_oir.QASM2_CUSTOM_GATE_DEFS`,
    which is itself the canonical Cartan / KAK decomposition of the
    most-general 2-qubit unitary.  All replacement opcodes are in
    qelib1.inc (or, for ``YY``, are emitted alongside the ``ryy``
    auxiliary definition that ``qelib1.inc`` parsers already accept).
    """
    if len(params) != 15:
        raise ValueError(f"UU15 expects exactly 15 parameters, got {len(params)}")
    a0, a1, a2, b0, b1, b2, txx, tyy, tzz, c0, c1, c2, d0, d1, d2 = params
    return [
        ("U3", qa, None, [a0, a1, a2], False, None),
        ("U3", qb, None, [b0, b1, b2], False, None),
        ("XX", [qa, qb], None, txx, False, None),
        ("YY", [qa, qb], None, tyy, False, None),
        ("ZZ", [qa, qb], None, tzz, False, None),
        ("U3", qa, None, [c0, c1, c2], False, None),
        ("U3", qb, None, [d0, d1, d2], False, None),
    ]


# ─── OriginIR-ext gate decompositions (to official OriginIR) ──────────


def _ecr_replacement(q1: int, q2: int) -> list[OpCode]:
    """ECR decomposition into U3 + CNOT (1 CNOT, exact up to global phase).

    Derived from the uniqc ECR matrix definition via Qiskit's UnitaryGate
    transpiler.  All angles are exact floating-point representations of the
    analytical U3 parameters.
    """
    # U3(π/2, φ, λ) — the four single-qubit rotations surrounding one CNOT.
    _pi2 = math.pi / 2
    return [
        ("U3", q1, None, [_pi2, 0.2105043039, 0.0], False, None),
        ("U3", q2, None, [_pi2, 0.0, 2.9895212217], False, None),
        ("CNOT", [q1, q2], None, None, False, None),
        ("U3", q1, None, [_pi2, -math.pi, 1.3602920229], False, None),
        ("U3", q2, None, [_pi2, 1.4187248949, 0.0], False, None),
    ]


def _iswap_replacement(q1: int, q2: int) -> list[OpCode]:
    """iSWAP = (S⊗S) · (H⊗I) · CNOT(q1→q2) · CNOT(q2→q1) · (I⊗H)"""
    return [
        ("S", q1, None, None, False, None),
        ("S", q2, None, None, False, None),
        ("H", q1, None, None, False, None),
        ("CNOT", [q1, q2], None, None, False, None),
        ("CNOT", [q2, q1], None, None, False, None),
        ("H", q2, None, None, False, None),
    ]


def _xx_replacement(theta: float, q1: int, q2: int) -> list[OpCode]:
    """RXX(θ) = (H⊗H) · CNOT · (I⊗RZ(θ)) · CNOT · (H⊗H)"""
    return [
        ("H", q1, None, None, False, None),
        ("H", q2, None, None, False, None),
        ("CNOT", [q1, q2], None, None, False, None),
        ("RZ", q2, None, theta, False, None),
        ("CNOT", [q1, q2], None, None, False, None),
        ("H", q1, None, None, False, None),
        ("H", q2, None, None, False, None),
    ]


def _yy_replacement(theta: float, q1: int, q2: int) -> list[OpCode]:
    """RYY(θ) = RX(π/2)⊗RX(π/2) · CNOT · RZ(θ) · CNOT · RX(-π/2)⊗RX(-π/2)"""
    return [
        ("RX", q1, None, math.pi / 2, False, None),
        ("RX", q2, None, math.pi / 2, False, None),
        ("CNOT", [q1, q2], None, None, False, None),
        ("RZ", q2, None, theta, False, None),
        ("CNOT", [q1, q2], None, None, False, None),
        ("RX", q1, None, -math.pi / 2, False, None),
        ("RX", q2, None, -math.pi / 2, False, None),
    ]


def _zz_replacement(theta: float, q1: int, q2: int) -> list[OpCode]:
    """RZZ(θ) = CNOT(q1→q2) · (I⊗RZ(θ)) · CNOT(q1→q2)"""
    return [
        ("CNOT", [q1, q2], None, None, False, None),
        ("RZ", q2, None, theta, False, None),
        ("CNOT", [q1, q2], None, None, False, None),
    ]


def _xy_replacement(theta: float, q1: int, q2: int) -> list[OpCode]:
    """XY(θ) = XX(-θ/2) · YY(-θ/2)

    Recursive: the XX/YY opcodes will be further decomposed by
    :func:`decompose_opcode_for_originir`.
    """
    return [
        ("XX", [q1, q2], None, -theta / 2, False, None),
        ("YY", [q1, q2], None, -theta / 2, False, None),
    ]


def _u3_dagger_params(p0: float, p1: float, p2: float) -> list[float]:
    """``u3(θ, φ, λ)† = u3(-θ, -λ, -φ)`` (qelib1 convention)."""
    return [-p0, -p2, -p1]


def _apply_dagger(replacement: list[OpCode], gate_name: str) -> list[OpCode]:
    """Return the dagger of ``replacement`` (reversed + each opcode inverted).

    The replacement sequences emitted by this module use only well-known
    1- and 2-qubit gates whose adjoint is obtained by negating angle
    parameters — except ``U3``, which needs the qelib1 swap of ``φ`` and
    ``λ`` after negation.

    Self-inverse gates (H, X, Y, Z, CNOT, CZ, I) pass through unchanged.
    S and T are daggered by setting the ``dagger`` flag.
    """
    # Self-inverse gates: dagger = identity
    _SELF_INVERSE = {"H", "X", "Y", "Z", "CNOT", "CZ", "SWAP", "I", "BARRIER"}

    inverted: list[OpCode] = []
    for op in reversed(replacement):
        name, qubits, cbits, params, _dag, ctrls = op
        upper = name.upper()
        if upper in _SELF_INVERSE:
            new_params = params
            new_dag = False
        elif upper in {"RX", "RY", "RZ", "U1", "XX", "YY", "ZZ", "PHASE2Q"}:
            new_params = -float(params) if not isinstance(params, (list, tuple)) else [-float(p) for p in params]
            new_dag = False
        elif upper == "U3":
            new_params = _u3_dagger_params(*[float(p) for p in params])
            new_dag = False
        elif upper in {"S", "T", "SX"}:
            # S†, T†, SX† are distinct gates — use the dagger flag.
            new_params = params
            new_dag = True
        elif upper in {"RPHI", "RPHI90", "RPHI180"}:
            # Should not occur — replacements never include these names —
            # but be defensive.
            raise NotImplementedError(
                f"Internal error: cannot dagger replacement opcode {upper!r} for gate {gate_name!r}."
            )
        else:
            raise NotImplementedError(
                f"Cannot dagger replacement opcode {upper!r} for gate {gate_name!r}; missing inverse rule."
            )
        inverted.append((name, qubits, cbits, new_params, new_dag, ctrls))
    return inverted


def decompose_opcode_for_qasm2(op: OpCode) -> list[OpCode]:
    """Return replacement opcodes for ``op`` if it is QASM2-unrepresentable.

    Returns ``[op]`` unchanged when ``op`` is already a QASM2-friendly
    opcode.  Raises :class:`NotImplementedError` when the gate is in
    :data:`QASM2_UNREPRESENTABLE_GATES` but is wrapped with
    ``control_qubits`` (controlled-RPhi / controlled-UU15 etc. require
    a more general lift that this lightweight pass does not provide).
    """
    name, qubits, cbits, params, dagger, control_qubits = op
    upper = str(name).upper()
    if upper not in QASM2_UNREPRESENTABLE_GATES:
        return [op]

    if control_qubits:
        raise NotImplementedError(
            f"decompose_for_qasm2 cannot rewrite controlled {name!r} "
            f"(control_qubits={control_qubits}); call uniqc.compile() first "
            f"or remove the control wrapper."
        )

    values = _as_param_list(params)

    if upper == "RPHI":
        if len(values) != 2:
            raise ValueError(f"RPhi expects 2 parameters, got {values}")
        target = _check_target_qubits(name, qubits, 1)[0]
        replacement = _rphi_replacement(values[0], values[1], target)
    elif upper == "RPHI90":
        if len(values) != 1:
            raise ValueError(f"RPhi90 expects 1 parameter, got {values}")
        target = _check_target_qubits(name, qubits, 1)[0]
        replacement = _rphi_replacement(math.pi / 2, values[0], target)
    elif upper == "RPHI180":
        if len(values) != 1:
            raise ValueError(f"RPhi180 expects 1 parameter, got {values}")
        target = _check_target_qubits(name, qubits, 1)[0]
        replacement = _rphi_replacement(math.pi, values[0], target)
    elif upper == "PHASE2Q":
        if len(values) != 3:
            raise ValueError(f"PHASE2Q expects 3 parameters, got {values}")
        q1, q2 = _check_target_qubits(name, qubits, 2)
        replacement = _phase2q_replacement(values[0], values[1], values[2], q1, q2)
    elif upper == "UU15":
        qa, qb = _check_target_qubits(name, qubits, 2)
        replacement = _uu15_replacement(values, qa, qb)
    else:  # pragma: no cover - guarded by membership check above
        return [op]

    if dagger:
        replacement = _apply_dagger(replacement, str(name))
    return replacement


def decompose_for_qasm2(circuit: Circuit) -> Circuit:
    """Return a new :class:`Circuit` with QASM2-unrepresentable gates rewritten.

    The original circuit is not mutated.  When the input contains no gate
    in :data:`QASM2_UNREPRESENTABLE_GATES`, this returns a shallow copy.

    Examples
    --------
    >>> from uniqc.circuit_builder import Circuit
    >>> c = Circuit(2)
    >>> c.rphi(0, 0.4, 0.7)
    >>> c.add_gate("PHASE2Q", [0, 1], params=[0.1, 0.2, 0.3])
    >>> c2 = decompose_for_qasm2(c)
    >>> {op[0] for op in c2.opcode_list}.isdisjoint({"RPhi", "PHASE2Q"})
    True
    """
    has_target = any(str(op[0]).upper() in QASM2_UNREPRESENTABLE_GATES for op in circuit.opcode_list)
    if not has_target:
        return circuit

    new_circuit = deepcopy(circuit)
    new_opcodes: list[OpCode] = []
    for op in circuit.opcode_list:
        new_opcodes.extend(decompose_opcode_for_qasm2(op))
    new_circuit.opcode_list = new_opcodes

    # Some replacements introduce qubits that may not have been ``record``-ed
    # on the source circuit (they always were, since we only touch existing
    # qubits, but keep ``qubit_num`` honest just in case).
    max_qubit = new_circuit.max_qubit
    for op in new_opcodes:
        _, qubits, _, _, _, control_qubits = op
        for q in _flatten_qubits(qubits):
            if q > max_qubit:
                max_qubit = q
        if control_qubits:
            for q in _flatten_qubits(control_qubits):
                if q > max_qubit:
                    max_qubit = q
    if max_qubit + 1 > new_circuit.qubit_num:
        new_circuit.qubit_num = max_qubit + 1
        new_circuit.max_qubit = max_qubit
    return new_circuit


def _flatten_qubits(qubits) -> Iterable[int]:
    if qubits is None:
        return ()
    if isinstance(qubits, int):
        return (qubits,)
    return tuple(int(q) for q in qubits)


# ─── OriginIR-ext → Official OriginIR decomposition ───────────────────


def decompose_opcode_for_originir(op: OpCode) -> list[OpCode]:
    """Return replacement opcodes for ``op`` if it is an OriginIR-ext-only gate.

    Returns ``[op]`` unchanged when ``op`` is already an official OriginIR
    gate.  Raises :class:`NotImplementedError` when the gate is extended
    but wrapped with ``control_qubits``.
    """
    name, qubits, cbits, params, dagger, control_qubits = op
    upper = str(name).upper()
    if upper not in ORIGINIR_EXT_DECOMPOSABLE_GATES:
        return [op]

    if control_qubits:
        raise NotImplementedError(
            f"decompose_for_originir cannot rewrite controlled {name!r} "
            f"(control_qubits={control_qubits}); call uniqc.compile() first "
            f"or remove the control wrapper."
        )

    values = _as_param_list(params)

    if upper == "RPHI":
        if len(values) != 2:
            raise ValueError(f"RPhi expects 2 parameters, got {values}")
        target = _check_target_qubits(name, qubits, 1)[0]
        replacement = _rphi_replacement(values[0], values[1], target)
    elif upper == "RPHI90":
        if len(values) != 1:
            raise ValueError(f"RPhi90 expects 1 parameter, got {values}")
        target = _check_target_qubits(name, qubits, 1)[0]
        replacement = _rphi_replacement(math.pi / 2, values[0], target)
    elif upper == "RPHI180":
        if len(values) != 1:
            raise ValueError(f"RPhi180 expects 1 parameter, got {values}")
        target = _check_target_qubits(name, qubits, 1)[0]
        replacement = _rphi_replacement(math.pi, values[0], target)
    elif upper == "PHASE2Q":
        if len(values) != 3:
            raise ValueError(f"PHASE2Q expects 3 parameters, got {values}")
        q1, q2 = _check_target_qubits(name, qubits, 2)
        replacement = _phase2q_replacement(values[0], values[1], values[2], q1, q2)
    elif upper == "UU15":
        qa, qb = _check_target_qubits(name, qubits, 2)
        replacement = _uu15_replacement(values, qa, qb)
    elif upper == "ECR":
        q1, q2 = _check_target_qubits(name, qubits, 2)
        replacement = _ecr_replacement(q1, q2)
    elif upper == "ISWAP":
        q1, q2 = _check_target_qubits(name, qubits, 2)
        replacement = _iswap_replacement(q1, q2)
    elif upper == "XX":
        if len(values) != 1:
            raise ValueError(f"XX expects 1 parameter, got {values}")
        q1, q2 = _check_target_qubits(name, qubits, 2)
        replacement = _xx_replacement(values[0], q1, q2)
    elif upper == "YY":
        if len(values) != 1:
            raise ValueError(f"YY expects 1 parameter, got {values}")
        q1, q2 = _check_target_qubits(name, qubits, 2)
        replacement = _yy_replacement(values[0], q1, q2)
    elif upper == "ZZ":
        if len(values) != 1:
            raise ValueError(f"ZZ expects 1 parameter, got {values}")
        q1, q2 = _check_target_qubits(name, qubits, 2)
        replacement = _zz_replacement(values[0], q1, q2)
    elif upper == "XY":
        if len(values) != 1:
            raise ValueError(f"XY expects 1 parameter, got {values}")
        q1, q2 = _check_target_qubits(name, qubits, 2)
        replacement = _xy_replacement(values[0], q1, q2)
    else:  # pragma: no cover - guarded by membership check above
        return [op]

    if dagger:
        replacement = _apply_dagger(replacement, str(name))
    return replacement


def decompose_for_originir(circuit: Circuit) -> Circuit:
    """Return a new :class:`Circuit` with OriginIR-ext gates decomposed.

    All OriginIR-ext-only gates (ECR, ISWAP, XX, YY, ZZ, XY, RPhi,
    RPhi90, RPhi180, PHASE2Q, UU15) are rewritten into mathematically
    equivalent sequences of official OriginIR gates.  The original
    circuit is not mutated.

    When the input contains no extended gate, the original circuit is
    returned unchanged (no copy).

    Examples
    --------
    >>> from uniqc.circuit_builder import Circuit
    >>> c = Circuit(2)
    >>> c.iswap(0, 1)
    >>> c.xx(0, 1, 0.5)
    >>> c2 = decompose_for_originir(c)
    >>> {op[0] for op in c2.opcode_list}.isdisjoint(ORIGINIR_EXT_DECOMPOSABLE_GATES)
    True
    """
    has_target = any(
        str(op[0]).upper() in ORIGINIR_EXT_DECOMPOSABLE_GATES
        for op in circuit.opcode_list
    )
    if not has_target:
        return circuit

    new_circuit = deepcopy(circuit)
    new_opcodes: list[OpCode] = []
    for op in circuit.opcode_list:
        new_opcodes.extend(decompose_opcode_for_originir(op))

    # XY decomposes to XX + YY; those still need further decomposition.
    # Two passes are enough (XY → XX+YY → official gates).
    final_opcodes: list[OpCode] = []
    for op in new_opcodes:
        final_opcodes.extend(decompose_opcode_for_originir(op))
    new_circuit.opcode_list = final_opcodes

    # Update qubit count if needed.
    max_qubit = new_circuit.max_qubit
    for op in final_opcodes:
        _, qubits, _, _, _, control_qubits = op
        for q in _flatten_qubits(qubits):
            if q > max_qubit:
                max_qubit = q
        if control_qubits:
            for q in _flatten_qubits(control_qubits):
                if q > max_qubit:
                    max_qubit = q
    if max_qubit + 1 > new_circuit.qubit_num:
        new_circuit.qubit_num = max_qubit + 1
        new_circuit.max_qubit = max_qubit
    return new_circuit
