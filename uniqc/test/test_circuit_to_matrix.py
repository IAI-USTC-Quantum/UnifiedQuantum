from __future__ import annotations

import numpy as np
import pytest

from uniqc.circuit_builder import Circuit
from uniqc.circuit_builder.matrix import NotMatrixableError, get_matrix


def test_to_matrix_matches_get_matrix():
    circuit = Circuit()
    circuit.h(0)
    circuit.cnot(0, 1)
    circuit.rz(1, 0.37)
    np.testing.assert_allclose(circuit.to_matrix(), get_matrix(circuit), atol=1e-12)


def test_to_matrix_qubit_zero_is_lsb():
    circuit = Circuit()
    circuit.x(0)
    matrix = circuit.to_matrix()
    assert matrix.shape == (2, 2)
    np.testing.assert_allclose(matrix[:, 0], [0, 1], atol=1e-12)

    two = Circuit()
    two.x(1)
    matrix = two.to_matrix()
    assert matrix.shape == (4, 4)
    # qubit 1 flipped: |00> -> |10> (index 2), qubit 0 stays the LSB.
    np.testing.assert_allclose(matrix[:, 0], [0, 0, 1, 0], atol=1e-12)


def test_to_matrix_bell_circuit_unitary():
    circuit = Circuit()
    circuit.h(0)
    circuit.cnot(0, 1)
    matrix = circuit.to_matrix()
    np.testing.assert_allclose(matrix.conj().T @ matrix, np.eye(4), atol=1e-12)
    bell = matrix[:, 0]
    np.testing.assert_allclose(np.abs(bell) ** 2, [0.5, 0, 0, 0.5], atol=1e-12)


def test_to_matrix_control_context_and_dagger():
    plain = Circuit()
    plain.h(0)
    with plain.control(0):
        plain.x(1)
    with plain.dagger():
        plain.rz(1, 0.5)
    matrix = plain.to_matrix()
    np.testing.assert_allclose(matrix.conj().T @ matrix, np.eye(4), atol=1e-12)


def test_to_matrix_rejects_measured_circuit():
    circuit = Circuit()
    circuit.h(0)
    circuit.measure(0)
    with pytest.raises(NotMatrixableError):
        circuit.to_matrix()


def test_to_matrix_matches_statevector_simulation():
    from uniqc.simulator import Simulator

    circuit = Circuit()
    circuit.h(0)
    circuit.rz(0, 0.25)
    circuit.cnot(0, 1)
    circuit.x(2)
    matrix = circuit.to_matrix()

    simulator = Simulator(least_qubit_remapping=False)
    simulator.simulate_preprocess(circuit.originir)
    for basis in range(matrix.shape[1]):
        prep = Circuit()
        for qubit in range(3):
            if (basis >> qubit) & 1:
                prep.x(qubit)
        prep.add_circuit(circuit)
        vector = np.asarray(simulator.simulate_statevector(prep.originir), dtype=complex)
        np.testing.assert_allclose(vector, matrix[:, basis], atol=1e-8)
