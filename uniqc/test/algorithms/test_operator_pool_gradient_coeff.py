"""Regression test for the coefficient-aware ADAPT-VQE parameter-shift rule.

``compute_operator_gradient`` builds two shifted circuits using
``_apply_cost_unitary``, which itself applies ``Rz(2γ·coeff)``.  The
correct shift in γ is ``π/(4|coeff|)``, and the gradient multiplier is
``|coeff|`` — not the textbook ``1/2`` that assumes a unit-coefficient
rotation.  Before the H-1 fix the function hard-coded ``shift = π/4`` and
divided by 2, producing values that disagreed with finite differences
whenever ``coeff ≠ 1``.

Here we compare the analytic gradient at γ = 0 against a centred
finite-difference for two distinct non-unit coefficients.
"""

from __future__ import annotations

import pytest

from uniqc.algorithms.core.ansatz._operator_pool import compute_operator_gradient
from uniqc.algorithms.core.ansatz._pauli_unitary import _apply_cost_unitary
from uniqc.algorithms.core.measurement.pauli_expectation import pauli_expectation
from uniqc.circuit_builder import Circuit


def _energy_at(base: Circuit, op_pauli: str, op_coeff: float, hamiltonian, gamma: float, n_qubits: int) -> float:
    c = Circuit(n_qubits)
    c.add_circuit(base)
    _apply_cost_unitary(c, [(op_pauli, op_coeff)], gamma)
    return sum(h_coeff * pauli_expectation(c, h_pauli, shots=None) for h_pauli, h_coeff in hamiltonian)


@pytest.mark.parametrize("coeff", [0.7, 2.0])
def test_operator_gradient_matches_finite_difference(coeff: float) -> None:
    n_qubits = 2
    base = Circuit(n_qubits)
    base.h(0)
    base.cx(0, 1)
    base.ry(1, 0.4)

    op_pauli = "X0X1"
    hamiltonian = [("Z0Z1", 1.0), ("X0", 0.3)]

    analytic = compute_operator_gradient(base, (op_pauli, coeff), hamiltonian, shots=None, n_qubits=n_qubits)

    eps = 1e-4
    e_plus = _energy_at(base, op_pauli, coeff, hamiltonian, +eps, n_qubits)
    e_minus = _energy_at(base, op_pauli, coeff, hamiltonian, -eps, n_qubits)
    fd = (e_plus - e_minus) / (2 * eps)

    # The function returns |gradient|; finite difference is signed.
    assert abs(analytic - abs(fd)) < 1e-3, f"coeff={coeff}: analytic={analytic}, |fd|={abs(fd)}"
