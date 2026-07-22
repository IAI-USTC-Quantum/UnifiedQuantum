"""Tests for two-qubit error models (TwoQubitDepolarizing, PauliError2Q).

Covers opcode shape, qubit-list propagation through all ErrorLoader variants,
and sanity checks on the generated probabilities / Pauli vectors.
"""

from __future__ import annotations

import pytest

from uniqc.simulator.error_model import (
    ErrorLoader_GateSpecificError,
    ErrorLoader_GateTypeError,
    ErrorLoader_GenericError,
    PauliError2Q,
    TwoQubitDepolarizing,
)

# ---------------------------------------------------------------------------
# Opcode shape: single opcode, qubit field is the full list
# ---------------------------------------------------------------------------

class TestTwoQubitDepolarizingOpcode:
    def test_returns_single_opcode(self):
        opcodes = TwoQubitDepolarizing(0.01).generate_error_opcode([0, 1])
        assert len(opcodes) == 1

    def test_qubit_field_is_list(self):
        opcodes = TwoQubitDepolarizing(0.01).generate_error_opcode([0, 1])
        _, qubits, _, _, _, _ = opcodes[0]
        assert isinstance(qubits, list)
        assert qubits == [0, 1]

    def test_probability_is_preserved(self):
        opcodes = TwoQubitDepolarizing(0.05).generate_error_opcode([2, 3])
        assert opcodes[0][3] == pytest.approx(0.05)

    def test_operation_name(self):
        opcodes = TwoQubitDepolarizing(0.01).generate_error_opcode([0, 1])
        assert opcodes[0][0] == "TwoQubitDepolarizing"

    def test_rejects_single_qubit(self):
        with pytest.raises(ValueError, match="two qubits"):
            TwoQubitDepolarizing(0.01).generate_error_opcode(0)

    def test_rejects_three_qubits(self):
        with pytest.raises(ValueError, match="two qubits"):
            TwoQubitDepolarizing(0.01).generate_error_opcode([0, 1, 2])


class TestPauliError2QOpcode:
    def test_returns_single_opcode(self):
        ps = [0.01] * 15
        opcodes = PauliError2Q(ps).generate_error_opcode([0, 1])
        assert len(opcodes) == 1

    def test_qubit_field_is_list(self):
        ps = [0.01] * 15
        opcodes = PauliError2Q(ps).generate_error_opcode([0, 1])
        _, qubits, _, _, _, _ = opcodes[0]
        assert isinstance(qubits, list)
        assert qubits == [0, 1]

    def test_parameter_is_preserved(self):
        ps = [0.01 * i for i in range(15)]
        opcodes = PauliError2Q(ps).generate_error_opcode([2, 3])
        assert opcodes[0][3] == ps

    def test_operation_name(self):
        opcodes = PauliError2Q([0.01] * 15).generate_error_opcode([0, 1])
        assert opcodes[0][0] == "PauliError2Q"

    def test_rejects_single_qubit(self):
        with pytest.raises(ValueError, match="two qubits"):
            PauliError2Q([0.01] * 15).generate_error_opcode(0)

    def test_rejects_three_qubits(self):
        with pytest.raises(ValueError, match="two qubits"):
            PauliError2Q([0.01] * 15).generate_error_opcode([0, 1, 2])


# ---------------------------------------------------------------------------
# Integration: qubit list survives through ErrorLoader processing
# ---------------------------------------------------------------------------

CNOT_OPCODE = ("CNOT", [0, 1], None, None, False, None)


class TestTwoQubitDepolarizingWithLoaders:
    """Regression test for #113: qubit field must be subscriptable after
    passing through an ErrorLoader."""

    @pytest.mark.parametrize("loader_cls", [
        ErrorLoader_GenericError,
        lambda ge: ErrorLoader_GateTypeError(ge, {}),
        lambda ge: ErrorLoader_GateSpecificError(ge, {}, {}),
    ])
    def test_generic_loader_propagates_qubit_list(self, loader_cls):
        error = TwoQubitDepolarizing(0.0154)
        loader = loader_cls([error])
        loader.process_opcodes([CNOT_OPCODE])

        error_opcodes = [op for op in loader.opcodes if op[0] == "TwoQubitDepolarizing"]
        assert len(error_opcodes) == 1
        _, qubits, _, _, _, _ = error_opcodes[0]
        assert isinstance(qubits, list), "qubit field must be a list, not int"
        assert qubits == [0, 1]

    def test_gatetype_loader_applies_to_cnot(self):
        error = TwoQubitDepolarizing(0.0154)
        loader = ErrorLoader_GateTypeError([], {"CNOT": [error]})
        loader.process_opcodes([CNOT_OPCODE])

        error_opcodes = [op for op in loader.opcodes if op[0] == "TwoQubitDepolarizing"]
        assert len(error_opcodes) == 1
        assert error_opcodes[0][1] == [0, 1]

    def test_gatespecific_loader_applies_to_cnot(self):
        error = TwoQubitDepolarizing(0.0154)
        loader = ErrorLoader_GateSpecificError([], {}, {("CNOT", (0, 1)): [error]})
        loader.process_opcodes([CNOT_OPCODE])

        error_opcodes = [op for op in loader.opcodes if op[0] == "TwoQubitDepolarizing"]
        assert len(error_opcodes) == 1
        assert error_opcodes[0][1] == [0, 1]

    def test_qubit_indices_survive_subscript(self):
        """The exact failure from #113: qubit[0] / qubit[1] must not raise."""
        error = TwoQubitDepolarizing(0.0154)
        loader = ErrorLoader_GateSpecificError([], {"CNOT": [error]}, {})
        loader.process_opcodes([CNOT_OPCODE])

        for op in loader.opcodes:
            qubit = op[1]
            if isinstance(qubit, list) and len(qubit) == 2:
                # This is what opcode_simulator does; must not raise
                _ = qubit[0], qubit[1]


class TestPauliError2QWithLoaders:
    @pytest.mark.parametrize("loader_cls", [
        ErrorLoader_GenericError,
        lambda ge: ErrorLoader_GateTypeError(ge, {}),
    ])
    def test_generic_loader_propagates_qubit_list(self, loader_cls):
        error = PauliError2Q([0.01] * 15)
        loader = loader_cls([error])
        loader.process_opcodes([CNOT_OPCODE])

        error_opcodes = [op for op in loader.opcodes if op[0] == "PauliError2Q"]
        assert len(error_opcodes) == 1
        _, qubits, _, _, _, _ = error_opcodes[0]
        assert isinstance(qubits, list)
        assert qubits == [0, 1]

    def test_gatetype_loader_applies_to_cnot(self):
        error = PauliError2Q([0.01] * 15)
        loader = ErrorLoader_GateTypeError([], {"CNOT": [error]})
        loader.process_opcodes([CNOT_OPCODE])

        error_opcodes = [op for op in loader.opcodes if op[0] == "PauliError2Q"]
        assert len(error_opcodes) == 1
        assert error_opcodes[0][1] == [0, 1]


# ---------------------------------------------------------------------------
# Multiple two-qubit gates in one circuit
# ---------------------------------------------------------------------------

class TestMultipleTwoQubitGates:
    def test_two_cnot_gates(self):
        error = TwoQubitDepolarizing(0.01)
        loader = ErrorLoader_GateTypeError([], {"CNOT": [error]})
        loader.process_opcodes([
            ("CNOT", [0, 1], None, None, False, None),
            ("CNOT", [1, 2], None, None, False, None),
        ])

        depol_opcodes = [op for op in loader.opcodes if op[0] == "TwoQubitDepolarizing"]
        assert len(depol_opcodes) == 2
        assert depol_opcodes[0][1] == [0, 1]
        assert depol_opcodes[1][1] == [1, 2]

    def test_mixed_one_and_two_qubit_gates(self):
        from uniqc.simulator.error_model import Depolarizing
        error_2q = TwoQubitDepolarizing(0.01)
        error_1q = Depolarizing(0.005)
        loader = ErrorLoader_GateTypeError(
            [error_1q],
            {"CNOT": [error_2q]},
        )
        loader.process_opcodes([
            ("HADAMARD", 0, None, None, False, None),
            ("CNOT", [0, 1], None, None, False, None),
            ("HADAMARD", 1, None, None, False, None),
        ])

        depol_1q = [op for op in loader.opcodes if op[0] == "Depolarizing"]
        depol_2q = [op for op in loader.opcodes if op[0] == "TwoQubitDepolarizing"]
        assert len(depol_1q) == 4   # 2 HADAMARDs (1 each) + CNOT generic (2, one per qubit)
        assert len(depol_2q) == 1   # only CNOT triggers TwoQubitDepolarizing
        assert depol_2q[0][1] == [0, 1]
