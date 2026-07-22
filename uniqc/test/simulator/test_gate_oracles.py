"""Cross-path oracle tests for every public unitary gate."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from uniqc.circuit_builder import Circuit
from uniqc.circuit_builder.matrix import get_matrix
from uniqc.compile.decompose import decompose_for_originir
from uniqc.simulator import MPSSimulator
from uniqc.simulator.opcode_simulator import OpcodeSimulator

pytestmark = pytest.mark.requires_cpp


@dataclass(frozen=True)
class GateCase:
    name: str
    wires: int | list[int]
    params: float | list[float] | None = None
    decomposable: bool = False
    mps: bool = False
    torch_virtual: bool = False

    @property
    def n_qubits(self) -> int:
        wires = [self.wires] if isinstance(self.wires, int) else self.wires
        return max(wires) + 1


_UU15_PARAMS = [
    0.11,
    -0.23,
    0.37,
    -0.41,
    0.53,
    -0.67,
    0.71,
    -0.83,
    0.97,
    -1.01,
    1.13,
    -1.27,
    1.31,
    -1.43,
    1.57,
]

GATE_CASES = [
    GateCase("I", 0, mps=True, torch_virtual=True),
    GateCase("X", 0, mps=True, torch_virtual=True),
    GateCase("Y", 0, mps=True, torch_virtual=True),
    GateCase("Z", 0, mps=True, torch_virtual=True),
    GateCase("H", 0, mps=True, torch_virtual=True),
    GateCase("S", 0, mps=True, torch_virtual=True),
    GateCase("T", 0, mps=True, torch_virtual=True),
    GateCase("SX", 0, mps=True, torch_virtual=True),
    GateCase("RX", 0, 0.37, mps=True, torch_virtual=True),
    GateCase("RY", 0, -0.53, mps=True, torch_virtual=True),
    GateCase("RZ", 0, 0.91, mps=True, torch_virtual=True),
    GateCase("U1", 0, -0.44, mps=True, torch_virtual=True),
    GateCase("U2", 0, [0.2, -0.7], mps=True, torch_virtual=True),
    GateCase("U3", 0, [0.4, -0.2, 0.8], mps=True, torch_virtual=True),
    GateCase("RPhi", 0, [0.6, -0.4], decomposable=True, mps=True),
    GateCase("RPhi90", 0, 0.3, decomposable=True, mps=True),
    GateCase("RPhi180", 0, -0.7, decomposable=True, mps=True),
    GateCase("CNOT", [0, 1], mps=True, torch_virtual=True),
    GateCase("CZ", [0, 1], mps=True, torch_virtual=True),
    GateCase("SWAP", [0, 1], mps=True, torch_virtual=True),
    GateCase("ISWAP", [0, 1], decomposable=True, mps=True, torch_virtual=True),
    GateCase("ECR", [0, 1], decomposable=True, mps=True),
    GateCase("XX", [0, 1], 0.37, decomposable=True, mps=True, torch_virtual=True),
    GateCase("YY", [0, 1], -0.53, decomposable=True, mps=True, torch_virtual=True),
    GateCase("ZZ", [0, 1], 0.91, decomposable=True, mps=True, torch_virtual=True),
    GateCase("XY", [0, 1], 0.63, decomposable=True, mps=True, torch_virtual=True),
    GateCase("PHASE2Q", [0, 1], [0.2, -0.4, 0.7], decomposable=True, mps=True),
    GateCase("UU15", [0, 1], _UU15_PARAMS, decomposable=True),
    GateCase("TOFFOLI", [0, 1, 2], torch_virtual=True),
    GateCase("CSWAP", [0, 1, 2], torch_virtual=True),
]


def _build_circuit(
    case: GateCase,
    *,
    dagger: bool,
    basis: int,
    n_qubits: int | None = None,
    wires: int | list[int] | None = None,
) -> Circuit:
    circuit = Circuit(n_qubits or case.n_qubits)
    for qubit in range(circuit.qubit_num):
        if (basis >> qubit) & 1:
            circuit.x(qubit)
    circuit.add_gate(
        case.name,
        case.wires if wires is None else wires,
        params=case.params,
        dagger=dagger,
    )
    return circuit


def _expected_state(circuit: Circuit) -> np.ndarray:
    state = np.zeros(2**circuit.qubit_num, dtype=np.complex128)
    state[0] = 1.0
    return get_matrix(circuit) @ state


def _assert_up_to_global_phase(actual: np.ndarray, expected: np.ndarray, atol: float = 1e-7) -> None:
    actual = np.asarray(actual, dtype=np.complex128).reshape(-1)
    expected = np.asarray(expected, dtype=np.complex128).reshape(-1)
    overlap = np.vdot(expected, actual)
    assert abs(overlap) > atol
    phase = overlap / abs(overlap)
    assert np.allclose(actual, phase * expected, atol=atol)


def _gate_matrix(
    case: GateCase,
    *,
    dagger: bool,
    n_qubits: int | None = None,
    wires: int | list[int] | None = None,
) -> np.ndarray:
    circuit = _build_circuit(case, dagger=dagger, basis=0, n_qubits=n_qubits, wires=wires)
    circuit.opcode_list = circuit.opcode_list[-1:]
    return get_matrix(circuit)


def _generic_input_circuit(
    case: GateCase,
    *,
    dagger: bool,
) -> Circuit:
    circuit = Circuit(case.n_qubits)
    for qubit in range(case.n_qubits):
        circuit.ry(qubit, 0.31 + 0.17 * qubit)
        circuit.rz(qubit, -0.23 + 0.19 * qubit)
    circuit.add_gate(case.name, case.wires, params=case.params, dagger=dagger)
    return circuit


@pytest.mark.parametrize("case", GATE_CASES, ids=lambda case: case.name)
@pytest.mark.parametrize("dagger", [False, True], ids=["plain", "dagger"])
def test_dense_statevector_and_density_match_matrix(case: GateCase, dagger: bool) -> None:
    statevector = OpcodeSimulator("statevector")
    density = OpcodeSimulator("density_operator")
    columns = []

    for basis in range(2**case.n_qubits):
        circuit = _build_circuit(case, dagger=dagger, basis=basis)
        actual = statevector.simulate_opcodes_statevector(circuit.qubit_num, circuit.opcode_list)
        columns.append(np.asarray(actual))

    _assert_up_to_global_phase(np.column_stack(columns), _gate_matrix(case, dagger=dagger))

    circuit = _generic_input_circuit(case, dagger=dagger)
    expected = _expected_state(circuit)
    actual_density = density.simulate_opcodes_density_operator(circuit.qubit_num, circuit.opcode_list)
    expected_density = np.outer(expected, expected.conj())
    assert np.allclose(actual_density, expected_density, atol=1e-7)


@pytest.mark.parametrize("case", [case for case in GATE_CASES if case.decomposable], ids=lambda case: case.name)
@pytest.mark.parametrize("dagger", [False, True], ids=["plain", "dagger"])
def test_official_decomposition_matches_matrix(case: GateCase, dagger: bool) -> None:
    simulator = OpcodeSimulator("statevector")
    columns = []

    for basis in range(2**case.n_qubits):
        circuit = _build_circuit(case, dagger=dagger, basis=basis)
        decomposed = decompose_for_originir(circuit)
        actual = simulator.simulate_opcodes_statevector(decomposed.qubit_num, decomposed.opcode_list)
        columns.append(np.asarray(actual))

    _assert_up_to_global_phase(np.column_stack(columns), _gate_matrix(case, dagger=dagger))


@pytest.mark.parametrize("case", [case for case in GATE_CASES if case.mps], ids=lambda case: case.name)
@pytest.mark.parametrize("dagger", [False, True], ids=["plain", "dagger"])
def test_mps_matches_matrix(case: GateCase, dagger: bool) -> None:
    simulator = MPSSimulator()
    columns = []

    for basis in range(2**case.n_qubits):
        circuit = _build_circuit(case, dagger=dagger, basis=basis)
        actual = simulator.simulate_statevector(circuit.originir)
        columns.append(np.asarray(actual))

    _assert_up_to_global_phase(np.column_stack(columns), _gate_matrix(case, dagger=dagger))


@pytest.mark.parametrize(
    "case",
    [
        GateCase("XY", [0, 1], 0.63),
        GateCase("PHASE2Q", [0, 1], [0.2, -0.4, 0.7]),
    ],
    ids=lambda case: case.name,
)
@pytest.mark.parametrize("dagger", [False, True], ids=["plain", "dagger"])
def test_qutip_density_matches_matrix_for_canonicalized_gates(case: GateCase, dagger: bool) -> None:
    pytest.importorskip("qutip")
    from uniqc.simulator import Simulator

    circuit = _generic_input_circuit(case, dagger=dagger)
    expected = _expected_state(circuit)
    actual = np.asarray(
        Simulator(
            backend_type="density_operator_qutip",
            least_qubit_remapping=False,
        ).simulate_density_matrix(circuit.originir)
    )
    assert np.allclose(actual, np.outer(expected, expected.conj()), atol=1e-7)


@pytest.mark.parametrize("case", [case for case in GATE_CASES if case.torch_virtual], ids=lambda case: case.name)
@pytest.mark.parametrize("dagger", [False, True], ids=["plain", "dagger"])
def test_torch_virtual_matches_matrix(case: GateCase, dagger: bool) -> None:
    torch = pytest.importorskip("torch")
    from uniqc.torch_adapter.expectation import _execute_opcodes
    columns = []

    for basis in range(2**case.n_qubits):
        circuit = _build_circuit(case, dagger=dagger, basis=basis)
        actual = _execute_opcodes(circuit.opcode_list, {}, circuit.qubit_num).reshape(-1)
        columns.append(actual.detach().cpu().numpy())
        assert torch.isfinite(actual).all()

    _assert_up_to_global_phase(np.column_stack(columns), _gate_matrix(case, dagger=dagger), atol=2e-6)


@pytest.mark.parametrize(
    "case",
    [
        GateCase("CNOT", [0, 2]),
        GateCase("CZ", [0, 2]),
        GateCase("SWAP", [0, 2]),
        GateCase("ISWAP", [0, 2]),
        GateCase("XX", [0, 2], 0.37),
        GateCase("YY", [0, 2], -0.53),
        GateCase("ZZ", [0, 2], 0.91),
        GateCase("XY", [0, 2], 0.63),
    ],
    ids=lambda case: case.name,
)
@pytest.mark.parametrize("dagger", [False, True], ids=["plain", "dagger"])
def test_torch_virtual_non_adjacent_two_qubit_gates(case: GateCase, dagger: bool) -> None:
    pytest.importorskip("torch")
    from uniqc.torch_adapter.expectation import _execute_opcodes
    columns = []

    for basis in range(8):
        circuit = _build_circuit(case, dagger=dagger, basis=basis, n_qubits=3)
        actual = _execute_opcodes(circuit.opcode_list, {}, 3).reshape(-1)
        columns.append(actual.detach().cpu().numpy())

    expected = _gate_matrix(case, dagger=dagger, n_qubits=3, wires=case.wires)
    _assert_up_to_global_phase(np.column_stack(columns), expected, atol=2e-6)
