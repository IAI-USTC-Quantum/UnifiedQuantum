"""Quantum Phase Estimation (QPE) circuit fragment.

Estimates the phase :math:`\\varphi \\in [0, 1)` of a unitary's eigenvalue
:math:`e^{2\\pi i\\varphi}` on a known eigenstate, using ``n_precision``
ancilla qubits encoding the binary fraction of :math:`\\varphi`.

The ``unitary_circuit`` is interpreted as a single application of :math:`U`
on a system register; QPE applies controlled :math:`U^{2^k}` for
``k = 0, 1, ..., n_precision - 1``.  Internally the controlled powers are
implemented by repeating the controlled :math:`U` ``2^k`` times — exact but
not necessarily efficient.  Callers wanting efficient :math:`U^{2^k}` (e.g.
HHL or Shor) should pre-compute and pass a custom callable via
``controlled_power``.

Layout convention
-----------------

- Qubits ``[0 .. n_system - 1]`` hold the system register.
- Qubits ``[n_system .. n_system + n_precision - 1]`` hold the precision
  register; qubit ``n_system`` is the *most* significant bit.
- The eigenstate is prepared by ``state_prep``; if ``None`` the system
  register is left in :math:`|0\\rangle^{\\otimes n_{\\text{system}}}`.
- The inverse QFT (no swaps) is applied to the precision register.
- ``MEASURE`` instructions are appended on the precision register so that
  the resulting integer ``m`` decoded as bitstring ``b_{n-1} ... b_0``
  satisfies :math:`\\tilde{\\varphi} = m / 2^{n_{\\text{precision}}}`.
"""

from __future__ import annotations

__all__ = ["qpe_circuit", "qpe_example"]

from typing import Callable, List, Optional

from uniqc.circuit_builder import Circuit

from .amplitude_estimation import _copy_circuit_gates_controlled
from .qft import qft_circuit


def _controlled_phase(fragment: Circuit, control: int, target: int, theta: float) -> None:
    """Apply controlled-phase :math:`CP(\\theta) = \\text{diag}(1,1,1,e^{i\\theta})`.

    Decomposed (up to a global phase) as
    ``RZ(θ/2)_c · CNOT(c,t) · RZ(-θ/2)_t · CNOT(c,t) · RZ(θ/2)_t``.
    """
    fragment.rz(control, theta / 2)
    fragment.cnot(control, target)
    fragment.rz(target, -theta / 2)
    fragment.cnot(control, target)
    fragment.rz(target, theta / 2)


def _inverse_qft_in_place(
    fragment: Circuit,
    qubits: List[int],
) -> None:
    """Apply textbook :math:`\\text{QFT}^\\dagger` (with bit-reversal swaps) on ``qubits``.

    Uses true controlled-phase gates so that the integer ``m`` decoded from
    the precision register's measurement reads naturally with cbit ``k``
    holding bit ``k`` of ``m``.
    """
    import math

    n = len(qubits)
    for j in reversed(range(n)):
        for k in reversed(range(j + 1, n)):
            angle = -math.pi / (2 ** (k - j))
            _controlled_phase(fragment, qubits[k], qubits[j], angle)
        fragment.h(qubits[j])
    for i in range(n // 2):
        fragment.swap(qubits[i], qubits[n - 1 - i])


def qpe_circuit(
    n_precision: int,
    unitary_circuit: Circuit,
    *,
    state_prep: Optional[Circuit] = None,
    controlled_power: Optional[Callable[[Circuit, Circuit, int, int], None]] = None,
    measure: bool = True,
) -> Circuit:
    """Build a Quantum Phase Estimation circuit fragment.

    Args:
        n_precision: Number of precision qubits (output bits of the phase
            estimate).  Must be ``>= 1``.
        unitary_circuit: A :class:`Circuit` representing one application of
            the unitary :math:`U` on the system register (qubit indices
            ``0 .. n_system - 1``).  The number of qubits in this fragment
            sets ``n_system``.
        state_prep: Optional :class:`Circuit` that prepares the eigenstate on
            the system register.  Must reference the same system qubits as
            ``unitary_circuit``.  If ``None``, the system register starts in
            :math:`|0\\rangle^{\\otimes n_{\\text{system}}}`.
        controlled_power: Optional override to supply an efficient
            implementation of controlled :math:`U^{2^k}`.  Signature::

                controlled_power(fragment, unitary, control_qubit, power)

            where ``power == 2 ** k``.  When ``None`` (the default) the
            controlled :math:`U` is repeated ``power`` times — correct but
            potentially slow for large ``n_precision``.
        measure: If ``True`` (default), append ``MEASURE`` instructions on
            the precision register at the end.  Set ``False`` if you want to
            chain QPE into a larger circuit before measuring.

    Returns:
        Fresh :class:`Circuit` with ``n_system + n_precision`` qubits.

    Raises:
        ValueError: ``n_precision < 1`` or ``unitary_circuit`` is empty.
    """
    if n_precision < 1:
        raise ValueError("qpe_circuit requires n_precision >= 1")
    n_system = unitary_circuit.max_qubit + 1
    if n_system < 1:
        raise ValueError(
            "qpe_circuit: unitary_circuit must contain at least one qubit"
        )

    system_qubits = list(range(n_system))
    precision_qubits = list(range(n_system, n_system + n_precision))

    fragment = Circuit()

    if state_prep is not None:
        fragment.add_circuit(state_prep)

    for q in precision_qubits:
        fragment.h(q)

    for k, ctrl in enumerate(precision_qubits):
        power = 1 << k  # 2 ** k
        if controlled_power is not None:
            controlled_power(fragment, unitary_circuit, ctrl, power)
        else:
            for _ in range(power):
                _copy_circuit_gates_controlled(unitary_circuit, fragment, ctrl)

    _inverse_qft_in_place(fragment, precision_qubits)

    if measure:
        for q in precision_qubits:
            fragment.measure(q)

    return fragment


def qpe_example() -> Circuit:
    """Return a small QPE demo: estimate the T-gate phase (1/8) with 4 precision bits."""
    import math

    u = Circuit()
    u.rz(0, math.pi / 4)  # T-gate-like phase on |1⟩

    state_prep = Circuit()
    state_prep.x(0)  # eigenstate |1⟩

    return qpe_circuit(
        n_precision=4,
        unitary_circuit=u,
        state_prep=state_prep,
    )
