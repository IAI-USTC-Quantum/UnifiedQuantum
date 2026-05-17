"""Regression test for the Y-basis inverse ordering in ``_apply_cost_unitary``.

Before the C-1 fix, the undo step in ``_apply_cost_unitary`` applied
``Rz(+π/2)`` *before* ``H`` for Y-Pauli terms.  That sequence produces the
matrix ``H · Rz(+π/2)``, which is **not** the inverse of the forward
``Rz(-π/2)`` → ``H`` sequence (whose matrix is ``H · Rz(-π/2)``).  The
correct inverse is ``Rz(+π/2) · H``, i.e. apply ``H`` first and then
``Rz(+π/2)``.  This test reconstructs the full single-qubit unitary
produced by the builder and compares it against the analytic
``exp(-i γ Y)`` for a handful of γ values.
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy.linalg import expm

from uniqc.algorithms.core.ansatz._pauli_unitary import _apply_cost_unitary
from uniqc.circuit_builder import Circuit
from uniqc.simulator import Simulator

_Y = np.array([[0.0, -1j], [1j, 0.0]], dtype=complex)


def _circuit_unitary(gamma: float) -> np.ndarray:
    """Build the 1-qubit unitary that ``_apply_cost_unitary`` produces for
    Hamiltonian ``1.0 * Y`` at parameter ``gamma`` by simulating its action
    on each computational basis state."""
    sim = Simulator(backend_type="statevector", least_qubit_remapping=False)
    cols = []
    for basis in (0, 1):
        c = Circuit(1)
        if basis == 1:
            c.x(0)
        _apply_cost_unitary(c, [("Y", 1.0)], gamma)
        cols.append(np.asarray(sim.simulate_statevector(c.originir), dtype=complex))
    return np.column_stack(cols)


@pytest.mark.parametrize("gamma", [0.1, 0.37, 1.0, -0.5])
def test_apply_cost_unitary_y_matches_expm(gamma: float) -> None:
    u_circuit = _circuit_unitary(gamma)
    u_exact = expm(-1j * gamma * _Y)
    np.testing.assert_allclose(u_circuit, u_exact, atol=1e-8, rtol=0)
