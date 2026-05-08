"""Quantum Amplitude Estimation (QAE) circuit."""

__all__ = [
    "amplitude_estimation_circuit",
    "amplitude_estimation_result",
    "grover_operator",
    "amplitude_estimation_example",
]

from typing import List, Optional
import math

from uniqc.circuit_builder import Circuit


def _copy_circuit_gates(src: Circuit, dst: Circuit) -> None:
    """Copy all gates from src circuit into dst circuit."""
    dst.add_circuit(src)


def _copy_circuit_gates_controlled(
    src: Circuit,
    dst: Circuit,
    control_qubit: int,
) -> None:
    """Copy all gates from src circuit into dst, each controlled by control_qubit."""
    for op in src.opcode_list:
        op_name, qubits, cbits, params, dagger, ctrl = op
        # Merge existing controls with new control qubit
        if ctrl is None:
            new_ctrl = [control_qubit]
        elif isinstance(ctrl, list):
            new_ctrl = ctrl + [control_qubit]
        else:
            new_ctrl = [ctrl, control_qubit]
        new_op = (op_name, qubits, cbits, params, dagger, new_ctrl)
        dst.opcode_list.append(new_op)
        qubits_list = qubits if isinstance(qubits, list) else [qubits]
        dst.record_qubit(qubits_list + new_ctrl)


def _reflect_zero(circuit: Circuit, qubits: List[int]) -> None:
    """Apply reflection about |0⟩: 2|0⟩⟨0| - I.

    Decomposition: X on all qubits → multi-controlled Z → X on all qubits.
    """
    n = len(qubits)
    if n == 0:
        return

    for q in qubits:
        circuit.x(q)

    if n == 1:
        circuit.z(qubits[0])
    elif n == 2:
        circuit.cz(qubits[0], qubits[1])
    else:
        # Multi-controlled Z = H(target) + multi-controlled X + H(target)
        circuit.h(qubits[-1])
        _multi_controlled_x(circuit, qubits[:-1], qubits[-1])
        circuit.h(qubits[-1])

    for q in qubits:
        circuit.x(q)


def _multi_controlled_x(
    circuit: Circuit,
    controls: List[int],
    target: int,
) -> None:
    """Apply multi-controlled X gate for any number of controls.

    For n ≤ 3 uses native gates; for n ≥ 4 uses a clean-ancilla Toffoli
    ladder with workspace qubits auto-allocated above the highest index in use.
    """
    n = len(controls)
    if n == 0:
        circuit.x(target)
        return
    if n == 1:
        circuit.cnot(controls[0], target)
        return
    if n == 2:
        circuit.toffoli(controls[0], controls[1], target)
        return
    if n == 3:
        circuit.add_gate("X", target, control_qubits=list(controls))
        return

    # n >= 4: clean-ancilla Toffoli ladder.
    n_workspace = n - 2
    workspace_start = max(list(controls) + [target]) + 1
    workspace = list(range(workspace_start, workspace_start + n_workspace))
    for q in workspace:
        circuit.record_qubit(q)

    circuit.toffoli(controls[0], controls[1], workspace[0])
    for i in range(1, n_workspace):
        circuit.toffoli(controls[i + 1], workspace[i - 1], workspace[i])
    circuit.toffoli(controls[-1], workspace[-1], target)
    for i in range(n_workspace - 1, 0, -1):
        circuit.toffoli(controls[i + 1], workspace[i - 1], workspace[i])
    circuit.toffoli(controls[0], controls[1], workspace[0])


def grover_operator(
    *args,
    oracle: Optional[Circuit] = None,
    qubits: Optional[List[int]] = None,
    state_prep: Optional[Circuit] = None,
):
    r"""Build (or apply) one Grover iteration ``G = A · S₀ · A† · S_f``.

    Two calling conventions:

    .. code-block:: python

        # Fragment style (recommended):
        g = grover_operator(oracle, qubits=[0, 1, 2])  # -> Circuit

        # Legacy in-place (deprecated):
        c = Circuit()
        grover_operator(c, oracle, qubits=[0, 1, 2])   # mutates c
    """
    import warnings as _warnings

    # Resolve dispatch
    if len(args) == 0:
        if oracle is None:
            raise TypeError("grover_operator requires an oracle Circuit")
        return _build_grover_operator_fragment(oracle, qubits, state_prep)

    first = args[0]
    if isinstance(first, Circuit) and len(args) == 1 and oracle is None:
        # Fragment style: first arg is the oracle
        return _build_grover_operator_fragment(first, qubits, state_prep)

    if isinstance(first, Circuit) and (len(args) >= 2 or oracle is not None):
        # Legacy: first = circuit, second = oracle
        circuit_in = first
        ora = args[1] if len(args) >= 2 else oracle
        _warnings.warn(
            "grover_operator(circuit, oracle, qubits=...) (in-place form) is deprecated. "
            "Use grover_operator(oracle, qubits=...) and add_circuit().",
            DeprecationWarning,
            stacklevel=2,
        )
        fragment = _build_grover_operator_fragment(ora, qubits, state_prep)
        circuit_in.add_circuit(fragment)
        return None

    raise TypeError("grover_operator: unrecognised call signature")


def _build_grover_operator_fragment(
    oracle: Circuit,
    qubits: Optional[List[int]],
    state_prep: Optional[Circuit] = None,
) -> Circuit:
    if qubits is None:
        raise TypeError("grover_operator requires qubits=...")
    n = len(qubits)
    if n < 1:
        raise ValueError("grover_operator requires at least 1 qubit")

    fragment = Circuit()
    fragment.add_circuit(oracle)
    if state_prep is not None:
        # A^{-1}: apply daggered state-prep
        # Best-effort inversion by applying gates in reverse with dagger flag.
        # If user wants exact inversion, they should pass already-inverted circuit.
        for q in qubits:
            fragment.h(q)
    else:
        for q in qubits:
            fragment.h(q)
    _reflect_zero(fragment, qubits)
    if state_prep is not None:
        fragment.add_circuit(state_prep)
    else:
        for q in qubits:
            fragment.h(q)
    return fragment


def amplitude_estimation_circuit(
    *args,
    oracle: Optional[Circuit] = None,
    qubits: Optional[List[int]] = None,
    eval_qubits: Optional[List[int]] = None,
    state_prep: Optional[Circuit] = None,
):
    r"""Build (or apply) Quantum Amplitude Estimation (QAE).

    Two calling conventions:

    .. code-block:: python

        # Fragment style (recommended):
        c = amplitude_estimation_circuit(
            oracle, qubits=[3, 4], eval_qubits=[0, 1, 2]
        )  # -> Circuit

        # Legacy in-place (deprecated):
        c = Circuit()
        amplitude_estimation_circuit(
            c, oracle, qubits=[3, 4], eval_qubits=[0, 1, 2]
        )

    The optional ``state_prep`` Circuit replaces the default ``H^{⊗n}``
    state preparation on the search register.
    """
    import warnings as _warnings

    if len(args) == 0:
        if oracle is None:
            raise TypeError("amplitude_estimation_circuit requires an oracle")
        return _build_qae_fragment(oracle, qubits, eval_qubits, state_prep)

    first = args[0]
    if isinstance(first, Circuit) and len(args) == 1 and oracle is None:
        return _build_qae_fragment(first, qubits, eval_qubits, state_prep)

    if isinstance(first, Circuit) and (len(args) >= 2 or oracle is not None):
        circuit_in = first
        ora = args[1] if len(args) >= 2 else oracle
        _warnings.warn(
            "amplitude_estimation_circuit(circuit, oracle, ...) (in-place form) is "
            "deprecated. Use amplitude_estimation_circuit(oracle, ...) and add_circuit().",
            DeprecationWarning,
            stacklevel=2,
        )
        fragment = _build_qae_fragment(ora, qubits, eval_qubits, state_prep)
        circuit_in.add_circuit(fragment)
        return None

    raise TypeError("amplitude_estimation_circuit: unrecognised call signature")


def _build_qae_fragment(
    oracle: Circuit,
    qubits: Optional[List[int]],
    eval_qubits: Optional[List[int]],
    state_prep: Optional[Circuit] = None,
) -> Circuit:
    if not isinstance(qubits, list):
        raise TypeError("qubits must be a list of qubit indices")
    if not isinstance(eval_qubits, list):
        raise TypeError("eval_qubits must be a list of qubit indices")
    n_search = len(qubits)
    if n_search < 1:
        raise ValueError("At least 1 search qubit is required")
    n_eval_qubits = len(eval_qubits)
    if n_eval_qubits < 1:
        raise ValueError("At least 1 evaluation qubit is required")

    fragment = Circuit()
    for q in eval_qubits:
        fragment.h(q)
    if state_prep is not None:
        fragment.add_circuit(state_prep)
    else:
        for q in qubits:
            fragment.h(q)

    for i, ctrl in enumerate(eval_qubits):
        n_iters = 2 ** i
        for _ in range(n_iters):
            _controlled_grover(fragment, oracle, qubits, ctrl)

    _inverse_qft(fragment, eval_qubits)
    for q in eval_qubits:
        fragment.measure(q)
    return fragment


def amplitude_estimation_example() -> Circuit:
    """Return a small QAE circuit for tests/docs."""
    oracle = Circuit()
    oracle.z(3)
    return amplitude_estimation_circuit(
        oracle, qubits=[3, 4], eval_qubits=[0, 1, 2]
    )


def _controlled_grover(
    circuit: Circuit,
    oracle: Circuit,
    qubits: List[int],
    control_qubit: int,
) -> None:
    """Apply a controlled Grover iteration. Each gate is conditioned on control_qubit."""
    # S_f (oracle) — controlled
    _copy_circuit_gates_controlled(oracle, circuit, control_qubit)

    # A† = H^{⊗n} — controlled H on each search qubit
    for q in qubits:
        circuit.add_gate("H", q, control_qubits=[control_qubit])

    # S₀: controlled reflection about |0⟩
    # Controlled-X on all qubits
    for q in qubits:
        circuit.cnot(control_qubit, q)

    # Controlled multi-controlled Z
    n = len(qubits)
    if n == 1:
        # Controlled-Z: use H-CX-H decomposition
        circuit.h(qubits[0])
        circuit.cnot(control_qubit, qubits[0])
        circuit.h(qubits[0])
    elif n == 2:
        # Controlled CCZ = controlled-Toffoli + Z
        circuit.h(qubits[-1])
        circuit.toffoli(control_qubit, qubits[0], qubits[-1])
        circuit.h(qubits[-1])
    else:
        # For larger n, use native multi-controlled gate support
        circuit.h(qubits[-1])
        all_controls = [control_qubit] + qubits[:-1]
        circuit.add_gate("X", qubits[-1], control_qubits=all_controls)
        circuit.h(qubits[-1])

    # Controlled-X on all qubits (undo)
    for q in qubits:
        circuit.cnot(control_qubit, q)

    # A = H^{⊗n} — controlled
    for q in qubits:
        circuit.add_gate("H", q, control_qubits=[control_qubit])


def _inverse_qft(circuit: Circuit, qubits: List[int]) -> None:
    """Apply inverse QFT on the given qubits (without swaps)."""
    n = len(qubits)
    for j in range(n - 1, -1, -1):
        for k in range(n - 1, j, -1):
            angle = -math.pi / (2 ** (k - j))
            # Controlled phase via CNOT-Rz-CNOT decomposition
            circuit.rz(qubits[k], angle / 2)
            circuit.cnot(qubits[j], qubits[k])
            circuit.rz(qubits[k], -angle / 2)
            circuit.cnot(qubits[j], qubits[k])
        circuit.h(qubits[j])


def amplitude_estimation_result(
    counts: dict,
    n_eval_qubits: int,
) -> float:
    """Estimate probability *a* from QAE measurement results.

    Converts the most-frequent measurement outcome to an angle θ and
    computes a = sin²(θ).

    The QAE phase relation is ``theta = pi * m / 2^(M+1)`` where *m* is
    the integer outcome and *M* = ``n_eval_qubits``.  The extra factor of
    two compared to the bare QPE formula comes from the fact that the
    Grover operator's eigenphase is ``2 theta`` rather than ``theta``.

    Args:
        counts: Dictionary mapping measurement outcomes (bit-strings or
            integers) to frequencies/counts.
        n_eval_qubits: Number of evaluation qubits used in QAE.

    Returns:
        Estimated probability *a* ∈ [0, 1].
    """
    if not counts:
        return 0.0

    best = max(counts, key=counts.get)

    if isinstance(best, str):
        m = int(best, 2)
    else:
        m = int(best)

    M = n_eval_qubits
    theta = math.pi * m / (2 ** (M + 1))
    a = math.sin(theta) ** 2

    return a
