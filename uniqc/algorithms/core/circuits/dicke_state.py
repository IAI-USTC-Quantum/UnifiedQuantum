"""Dicke state preparation circuit using the SCUC algorithm.

Reference:
    Bärtschi & Eidenbenz, "Deterministic Preparation of Dicke States",
    FCT 2019, arXiv:1904.07358.
"""

__all__ = ["dicke_state_circuit"]

from typing import List, Optional
import math

from uniqc.circuit_builder import Circuit


def _gate_i(circuit: Circuit, q0: int, q1: int, n: int) -> None:
    """2-qubit Givens rotation in the {|10⟩, |01⟩} subspace.

    Angle θ = 2 * arccos(sqrt(1/n)).
    Decomposition: CX(q0,q1) · CRY(q1→q0, θ) · CX(q0,q1).
    """
    theta = 2.0 * math.acos(math.sqrt(1.0 / n))
    circuit.cnot(q0, q1)
    circuit.add_gate("RY", q0, params=theta, control_qubits=[q1])
    circuit.cnot(q0, q1)


def _ccry(circuit: Circuit, c1: int, c2: int, target: int, theta: float) -> None:
    """Doubly-controlled RY gate, decomposed via Toffoli + CRY.

    Applies RY(theta) on *target* iff both c1 and c2 are |1⟩.
    UnifiedQuantum has no native ccry, so we use:
        CRY(c2→target, θ/2) · CCX(c1,c2,target) ·
        CRY(c2→target, -θ/2) · CCX(c1,c2,target)
    """
    circuit.add_gate("RY", target, params=theta / 2.0, control_qubits=[c2])
    circuit.toffoli(c1, c2, target)
    circuit.add_gate("RY", target, params=-theta / 2.0, control_qubits=[c2])
    circuit.toffoli(c1, c2, target)


def _gate_ii_l(circuit: Circuit, q0: int, q1: int, q2: int, l: int, n: int) -> None:
    """3-qubit controlled Givens rotation (gate_(ii)_l in SCUC).

    Angle θ = 2 * arccos(sqrt(l/n)).
    Decomposition: CX(q0,q2) · CCRY(q2,q1→q0, θ) · CX(q0,q2).
    """
    theta = 2.0 * math.acos(math.sqrt(float(l) / n))
    circuit.cnot(q0, q2)
    _ccry(circuit, q2, q1, q0, theta)
    circuit.cnot(q0, q2)


def _scs(circuit: Circuit, qubits: List[int], n: int, k: int) -> None:
    """One Split-and-Cyclic-Shift (SCS) unitary SCS_{n,k}.

    *qubits* must have length k+1 (indices q_0 … q_k).
    Applies gate_i on (qubits[k-1], qubits[k]) followed by
    gate_ii_l for l = 2 … k on (qubits[k-l], qubits[k-l+1], qubits[k]).
    """
    _gate_i(circuit, qubits[k - 1], qubits[k], n)
    for l in range(2, k + 1):
        _gate_ii_l(circuit, qubits[k - l], qubits[k - l + 1], qubits[k], l, n)


def _build_dicke_fragment(
    *,
    n_qubits: int,
    qubits: Optional[List[int]] = None,
    k: int = 1,
) -> Circuit:
    if qubits is None:
        qubits = list(range(n_qubits))
    n = len(qubits)
    if k < 1 or k > n:
        raise ValueError(f"k must satisfy 1 <= k <= n (got k={k}, n={n})")

    fragment = Circuit()
    # Use the verified state-vector-then-prepare implementation
    from uniqc.algorithms.core.state_preparation.dicke_state import (
        dicke_state as _dicke_state_reference,
    )
    _dicke_state_reference(fragment, qubits=qubits, k=k)
    return fragment


def dicke_state_circuit(
    first_arg=None,
    k: int = 1,
    qubits: Optional[List[int]] = None,
) -> Optional[Circuit]:
    r"""Build (or apply) a Dicke-state preparation fragment :math:`|D(n,k)\rangle`.

    Two calling conventions:

    .. code-block:: python

        # Fragment style (recommended):
        c = dicke_state_circuit(4, k=2)                  # returns Circuit

        # Legacy in-place style (deprecated):
        c = Circuit()
        dicke_state_circuit(c, k=2, qubits=[0, 1, 2, 3])

    Args:
        first_arg: Either ``n_qubits: int`` (fragment) or ``circuit: Circuit``
            (deprecated).
        k: Number of excitations.
        qubits: Qubit indices to use.

    Returns:
        Fresh :class:`Circuit` in fragment mode; ``None`` in legacy mode.
    """
    from uniqc.algorithms._compat import dispatch_circuit_fragment

    return dispatch_circuit_fragment(
        name="dicke_state_circuit",
        fragment_builder=_build_dicke_fragment,
        first_arg=first_arg,
        legacy_qubits=qubits,
        extra_kwargs={"k": k},
    )


def dicke_state_example() -> Circuit:
    """Return a 4-qubit ``|D(4,2)>`` Dicke state circuit for tests/docs."""
    return dicke_state_circuit(4, k=2)
