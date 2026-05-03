from __future__ import annotations

import math
from collections.abc import Iterable

import numpy as np
import pytest
import qiskit  # noqa: F401

from uniqc.backend_adapter.backend_info import BackendInfo, Platform, QubitTopology
from uniqc.circuit_builder import Circuit
from uniqc.circuit_builder.matrix import NotMatrixableError, _opcode_matrix, get_matrix
from uniqc.compile import compile
from uniqc.compile.compiler import _originir_to_circuit
from uniqc.compile.originir.originir_line_parser import OriginIR_LineParser


def _assert_same_up_to_global_phase(
    actual: np.ndarray,
    expected: np.ndarray,
    *,
    atol: float = 1e-8,
) -> None:
    assert actual.shape == expected.shape
    overlap = np.vdot(expected.ravel(), actual.ravel())
    assert abs(overlap) > atol
    phase = overlap / abs(overlap)
    assert np.allclose(actual, phase * expected, atol=atol)


@pytest.fixture
def all_to_all_6q_info() -> BackendInfo:
    return BackendInfo(
        platform=Platform.ORIGINQ,
        name="all_to_all_6q",
        num_qubits=6,
        topology=tuple(QubitTopology(u=i, v=j) for i in range(6) for j in range(i + 1, 6)),
    )


def _as_qubits(qubits: int | Iterable[int] | None) -> list[int]:
    if qubits is None:
        return []
    if isinstance(qubits, int):
        return [qubits]
    return [int(q) for q in qubits]


def _parse_originir(originir: str):
    opcodes = []
    measurements: dict[int, int] = {}

    for line in originir.strip().splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        op, qubits, cbit, params, dagger, controls = OriginIR_LineParser.parse_line(stripped)
        if op in {"QINIT", "CREG", "BARRIER"}:
            continue
        if op == "MEASURE":
            measurements[int(cbit)] = int(qubits)
            continue
        if op in {"CONTROL", "ENDCONTROL", "DAGGER", "ENDDAGGER", "DEF", "ENDDEF"}:
            continue
        opcodes.append((op, qubits, params, bool(dagger), controls))

    return opcodes, measurements


def _active_qubits(opcodes, measurements: dict[int, int]) -> list[int]:
    qubits = set(measurements.values())
    for _op, targets, _params, _dagger, controls in opcodes:
        qubits.update(_as_qubits(targets))
        qubits.update(_as_qubits(controls))
    return sorted(qubits)


def _apply_gate_to_state(state: np.ndarray, gate: np.ndarray, qubits: list[int], n_qubits: int) -> np.ndarray:
    tensor = state.reshape((2,) * n_qubits, order="F")
    gate_tensor = gate.reshape((2,) * (2 * len(qubits)), order="F")
    gate_inputs = list(range(n_qubits, n_qubits + len(qubits)))
    output_labels = list(range(n_qubits))
    state_labels = output_labels.copy()

    for local_index, qubit in enumerate(qubits):
        state_labels[qubit] = gate_inputs[local_index]

    evolved = np.einsum(
        gate_tensor,
        [output_labels[q] for q in qubits] + gate_inputs,
        tensor,
        state_labels,
        output_labels,
    )
    return evolved.reshape((2**n_qubits,), order="F")


def _simulate_probabilities_np(originir: str, *, max_qubits: int = 10) -> np.ndarray:
    opcodes, measurements = _parse_originir(originir)
    if not measurements:
        raise AssertionError("compiler probability tests require explicit measurements")

    labels = _active_qubits(opcodes, measurements)
    if len(labels) > max_qubits:
        raise AssertionError(f"statevector test supports at most {max_qubits} active qubits, got {len(labels)}")
    label_to_pos = {label: pos for pos, label in enumerate(labels)}

    state = np.zeros(2 ** len(labels), dtype=np.complex128)
    state[0] = 1.0

    for name, qubits, params, dagger, controls in opcodes:
        compact_targets = [label_to_pos[q] for q in _as_qubits(qubits)]
        compact_controls = [label_to_pos[q] for q in _as_qubits(controls)]
        compact_qubits = compact_targets[0] if isinstance(qubits, int) else compact_targets
        gate, gate_qubits = _opcode_matrix(name, compact_qubits, params, dagger, compact_controls or None)
        state = _apply_gate_to_state(state, gate, gate_qubits, len(labels))

    n_cbits = max(measurements) + 1
    probabilities = np.zeros(2**n_cbits, dtype=float)

    for basis_index, amplitude in enumerate(state):
        measured_index = 0
        for cbit, qubit_label in measurements.items():
            measured_index |= ((basis_index >> label_to_pos[qubit_label]) & 1) << cbit
        probabilities[measured_index] += float(abs(amplitude) ** 2)

    return probabilities


def _simulate_probabilities_qutip(originir: str) -> np.ndarray:
    import qutip

    opcodes, measurements = _parse_originir(originir)
    labels = _active_qubits(opcodes, measurements)
    label_to_pos = {label: pos for pos, label in enumerate(labels)}
    n_qubits = len(labels)
    state = qutip.basis([2] * n_qubits, [0] * n_qubits)

    for name, qubits, params, dagger, controls in opcodes:
        compact_targets = [label_to_pos[q] for q in _as_qubits(qubits)]
        compact_controls = [label_to_pos[q] for q in _as_qubits(controls)]
        compact_qubits = compact_targets[0] if isinstance(qubits, int) else compact_targets
        gate, gate_qubits = _opcode_matrix(name, compact_qubits, params, dagger, compact_controls or None)
        operator = qutip.Qobj(_expand_operator_np(gate, gate_qubits, n_qubits), dims=[[2] * n_qubits, [2] * n_qubits])
        state = operator * state

    state_np = np.asarray(state.full()).reshape((2**n_qubits,))
    n_cbits = max(measurements) + 1
    probabilities = np.zeros(2**n_cbits, dtype=float)
    for basis_index, amplitude in enumerate(state_np):
        measured_index = 0
        for cbit, qubit_label in measurements.items():
            measured_index |= ((basis_index >> label_to_pos[qubit_label]) & 1) << cbit
        probabilities[measured_index] += float(abs(amplitude) ** 2)
    return probabilities


def _expand_operator_np(gate: np.ndarray, qubits: list[int], n_total: int) -> np.ndarray:
    dim = 2**n_total
    matrix = np.zeros((dim, dim), dtype=np.complex128)
    for col in range(dim):
        local_col = 0
        for local_index, qubit in enumerate(qubits):
            local_col |= ((col >> qubit) & 1) << local_index
        for local_row in range(2 ** len(qubits)):
            value = gate[local_row, local_col]
            if abs(value) == 0:
                continue
            row = col
            for qubit in qubits:
                row &= ~(1 << qubit)
            for local_index, qubit in enumerate(qubits):
                row |= ((local_row >> local_index) & 1) << qubit
            matrix[row, col] += value
    return matrix


def _apply_random_gate(circuit: Circuit, rng: np.random.Generator) -> None:
    gate = str(
        rng.choice(
            [
                "h",
                "x",
                "y",
                "z",
                "s",
                "t",
                "sx",
                "rx",
                "ry",
                "rz",
                "u1",
                "u2",
                "u3",
                "cx",
                "cz",
                "swap",
            ]
        )
    )

    if gate in {"h", "x", "y", "z", "s", "t", "sx"}:
        getattr(circuit, gate)(int(rng.integers(0, 6)))
        return

    if gate in {"rx", "ry", "rz", "u1"}:
        getattr(circuit, gate)(int(rng.integers(0, 6)), float(rng.uniform(-math.pi, math.pi)))
        return

    if gate == "u2":
        circuit.u2(
            int(rng.integers(0, 6)),
            float(rng.uniform(-math.pi, math.pi)),
            float(rng.uniform(-math.pi, math.pi)),
        )
        return

    if gate == "u3":
        circuit.u3(
            int(rng.integers(0, 6)),
            float(rng.uniform(-math.pi, math.pi)),
            float(rng.uniform(-math.pi, math.pi)),
            float(rng.uniform(-math.pi, math.pi)),
        )
        return

    q0, q1 = [int(q) for q in rng.choice(6, size=2, replace=False)]
    getattr(circuit, gate)(q0, q1)


def _random_measured_6q_circuit(seed: int, depth: int = 18) -> Circuit:
    rng = np.random.default_rng(seed)
    circuit = Circuit(6)

    circuit.h(0)
    circuit.rx(1, float(rng.uniform(-math.pi, math.pi)))
    circuit.ry(2, float(rng.uniform(-math.pi, math.pi)))
    circuit.rz(3, float(rng.uniform(-math.pi, math.pi)))
    circuit.cx(0, 4)
    circuit.cz(2, 5)
    circuit.swap(1, 3)

    for _ in range(depth):
        _apply_random_gate(circuit, rng)

    measured = list(range(6)) if seed % 2 == 0 else [int(q) for q in rng.choice(6, size=int(rng.integers(1, 6)), replace=False)]
    circuit.measure(*measured)
    return circuit


class TestGetMatrix:
    def test_single_qubit_gate_on_declared_padding(self):
        circuit = Circuit(6)
        circuit.x(0)
        matrix = get_matrix(circuit)
        assert matrix.shape == (64, 64)
        assert np.allclose(matrix[:, 0], np.eye(64)[:, 1])

    def test_gates_apply_in_circuit_order(self):
        circuit = Circuit(1)
        circuit.x(0)
        circuit.z(0)
        assert np.allclose(get_matrix(circuit)[:, 0], [0, -1])

    def test_cnot_uses_first_qubit_as_control(self):
        circuit = Circuit(2)
        circuit.cx(0, 1)
        matrix = get_matrix(circuit)
        assert np.allclose(matrix[:, 1], [0, 0, 0, 1])
        assert np.allclose(matrix[:, 3], [0, 1, 0, 0])

    def test_swap_exchanges_local_bits(self):
        circuit = Circuit(2)
        circuit.swap(0, 1)
        matrix = get_matrix(circuit)
        assert np.allclose(matrix[:, 1], [0, 0, 1, 0])
        assert np.allclose(matrix[:, 2], [0, 1, 0, 0])

    def test_toffoli_flips_target_when_both_controls_are_one(self):
        circuit = Circuit(3)
        circuit.toffoli(0, 1, 2)
        matrix = get_matrix(circuit)
        assert np.allclose(matrix[:, 3], np.eye(8)[:, 7])
        assert np.allclose(matrix[:, 7], np.eye(8)[:, 3])

    def test_measure_is_rejected(self):
        circuit = Circuit(1)
        circuit.measure(0)
        with pytest.raises(NotMatrixableError):
            get_matrix(circuit)

    def test_get_matrix_matches_qutip_evolution(self):
        import qutip  # noqa: F401

        circuit = Circuit(3)
        circuit.h(0)
        circuit.rx(1, 0.17)
        circuit.cx(0, 2)
        circuit.ry(2, -0.31)

        originir = circuit.originir + "MEASURE q[0], c[0]\nMEASURE q[1], c[1]\nMEASURE q[2], c[2]\n"
        np_from_matrix = np.abs(get_matrix(circuit)[:, 0]) ** 2
        qutip_probabilities = _simulate_probabilities_qutip(originir)
        assert np.allclose(np_from_matrix, qutip_probabilities)


def test_probability_simulator_compacts_high_qubit_labels():
    originir = """
QINIT 36
CREG 2
H q[35]
CNOT q[35], q[12]
MEASURE q[12], c[0]
MEASURE q[35], c[1]
"""
    assert np.allclose(_simulate_probabilities_np(originir), [0.5, 0.0, 0.0, 0.5])


def test_originir_to_circuit_orders_measurements_by_cbit():
    circuit = _originir_to_circuit(
        """
QINIT 36
CREG 2
H q[35]
MEASURE q[35], c[1]
MEASURE q[12], c[0]
"""
    )
    assert circuit.measure_list == [12, 35]
    assert circuit.cbit_num == 2


def test_compile_preserves_50_random_6q_measurement_probabilities(all_to_all_6q_info: BackendInfo):
    for seed in range(50):
        circuit = _random_measured_6q_circuit(seed)
        compiled_originir = compile(circuit, all_to_all_6q_info, output_format="originir", level=1)

        original_probabilities = _simulate_probabilities_np(circuit.originir)
        compiled_probabilities = _simulate_probabilities_np(compiled_originir)

        assert np.allclose(compiled_probabilities, original_probabilities, atol=1e-7), f"seed={seed}"
