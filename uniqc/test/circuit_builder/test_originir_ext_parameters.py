"""Tests for OriginIR-ext symbolic parameter support.

Covers the ``PARAM`` header + inline symbolic-expression round-trip between
:class:`~uniqc.circuit_builder.Circuit` and OriginIR-ext text, the
``Circuit.assign_parameters`` binding API, and the guards that reject unbound
circuits on export / simulation.
"""

import numpy as np
import pytest

from uniqc.circuit_builder import Circuit
from uniqc.circuit_builder.parameter import Parameter, Parameters
from uniqc.exceptions import CircuitTranslationError
from uniqc.simulator import Simulator

# =============================================================================
# Parameter core additions (unbind, array metadata)
# =============================================================================


class TestParameterCore:
    def test_unbind_restores_symbolic_state(self):
        p = Parameter("theta")
        p.bind(1.0)
        assert p.is_bound
        p.unbind()
        assert not p.is_bound
        # After unbind, evaluate() consults the provided values dict again.
        assert p.evaluate({"theta": 2.0}) == 2.0

    def test_parameters_unbind(self):
        arr = Parameters("alpha", 3)
        arr.bind([0.1, 0.2, 0.3])
        assert arr[0].is_bound
        arr.unbind()
        assert not any(p.is_bound for p in arr)

    def test_parameters_array_metadata(self):
        arr = Parameters("alpha", 4)
        p = arr[2]
        assert p._array_name == "alpha"
        assert p._array_index == 2
        assert p._array_size == 4

    def test_standalone_parameter_has_no_array_metadata(self):
        assert Parameter("theta")._array_name is None


# =============================================================================
# Symbolic capture + introspection on Circuit
# =============================================================================


class TestSymbolicCapture:
    def test_free_parameters_and_is_parametric(self):
        theta, phi = Parameter("theta"), Parameter("phi")
        c = Circuit(2)
        c.rx(0, theta)
        c.ry(1, theta * 2 + phi / 3)
        assert c.is_parametric
        assert c.free_parameters == ["phi", "theta"]

    def test_non_parametric_circuit(self):
        c = Circuit(1)
        c.rx(0, 1.57)
        assert not c.is_parametric
        assert c.free_parameters == []

    def test_array_registration(self):
        arr = Parameters("alpha", 3)
        c = Circuit(1)
        c.rz(0, arr[1])
        assert c._param_arrays == {"alpha": 3}
        assert c.free_parameters == ["alpha_1"]


# =============================================================================
# Serialization: PARAM header + inline rendering
# =============================================================================


class TestSerialization:
    def test_scalar_param_header_and_reference(self):
        theta = Parameter("theta")
        c = Circuit(1)
        c.rx(0, theta)
        c.measure(0)
        ir = c.originir
        assert "PARAM theta" in ir
        assert "RX q[0], (theta)" in ir

    def test_expression_rendering(self):
        theta, phi = Parameter("theta"), Parameter("phi")
        c = Circuit(1)
        c.rx(0, theta * 2 + phi / 3)
        ir = c.originir
        assert "PARAM phi" in ir
        assert "PARAM theta" in ir
        # sympy canonicalises the expression but keeps both symbols.
        assert "theta" in ir and "phi" in ir

    def test_array_rendering_uses_bracket_syntax(self):
        arr = Parameters("alpha", 3)
        c = Circuit(1)
        c.rz(0, arr[1])
        ir = c.originir
        assert "PARAM alpha[3]" in ir
        assert "RZ q[0], (alpha[1])" in ir

    def test_non_parametric_serialization_unchanged(self):
        c = Circuit(1)
        c.rx(0, 1.57)
        c.measure(0)
        assert "PARAM" not in c.originir


# =============================================================================
# Round-trip: from_originir(c.originir).originir == c.originir
# =============================================================================


class TestRoundTrip:
    def _assert_roundtrip(self, c: Circuit):
        ir = c.originir
        parsed = Circuit.from_originir(ir)
        assert parsed.originir == ir
        assert parsed.free_parameters == c.free_parameters
        assert parsed._param_arrays == c._param_arrays

    def test_roundtrip_scalar(self):
        theta = Parameter("theta")
        c = Circuit(1)
        c.rx(0, theta)
        c.measure(0)
        self._assert_roundtrip(c)

    def test_roundtrip_expression(self):
        theta, phi = Parameter("theta"), Parameter("phi")
        c = Circuit(2)
        c.rx(0, theta)
        c.ry(1, theta * 2 + phi / 3)
        c.measure(0, 1)
        self._assert_roundtrip(c)

    def test_roundtrip_array(self):
        arr = Parameters("alpha", 3)
        c = Circuit(2)
        c.rz(0, arr[0])
        c.rz(1, arr[2])
        c.measure(0, 1)
        self._assert_roundtrip(c)

    def test_roundtrip_mixed(self):
        theta, phi = Parameter("theta"), Parameter("phi")
        arr = Parameters("alpha", 3)
        c = Circuit(2)
        c.rx(0, theta)
        c.ry(1, theta * 2 + phi / 3)
        c.rz(0, arr[1])
        c.u3(1, arr[0], phi, 0.5)
        c.measure(0, 1)
        self._assert_roundtrip(c)

    def test_parse_bracket_reference_maps_to_element_symbol(self):
        ir = "QINIT 1\nCREG 1\nPARAM alpha[3]\nRZ q[0], (alpha[1])\nMEASURE q[0], c[0]\n"
        c = Circuit.from_originir(ir)
        assert c.free_parameters == ["alpha_1"]
        assert c._param_arrays == {"alpha": 3}


# =============================================================================
# assign_parameters
# =============================================================================


class TestAssignParameters:
    def test_bind_by_name(self):
        theta = Parameter("theta")
        c = Circuit(1)
        c.rx(0, theta)
        bound = c.assign_parameters({"theta": 0.5})
        assert not bound.is_parametric
        assert bound.opcode_list[0][3] == pytest.approx(0.5)

    def test_bind_by_parameter_object(self):
        theta = Parameter("theta")
        c = Circuit(1)
        c.rx(0, theta)
        bound = c.assign_parameters({theta: 0.5})
        assert not bound.is_parametric

    def test_bind_by_parameters_array(self):
        arr = Parameters("alpha", 3)
        c = Circuit(3)
        for i in range(3):
            c.rz(i, arr[i])
        bound = c.assign_parameters({arr: [0.1, 0.2, 0.3]})
        assert not bound.is_parametric
        assert [op[3] for op in bound.opcode_list] == pytest.approx([0.1, 0.2, 0.3])

    def test_bind_from_bound_parameters_object(self):
        arr = Parameters("alpha", 2)
        arr.bind([0.4, 0.5])
        c = Circuit(2)
        c.rz(0, arr[0])
        c.rz(1, arr[1])
        bound = c.assign_parameters(arr)
        assert [op[3] for op in bound.opcode_list] == pytest.approx([0.4, 0.5])

    def test_partial_binding_keeps_remaining_symbolic(self):
        theta, phi = Parameter("theta"), Parameter("phi")
        c = Circuit(1)
        c.rx(0, theta * 2 + phi / 3)
        bound = c.assign_parameters({"theta": 1.0})
        assert bound.free_parameters == ["phi"]

    def test_non_mutating_by_default(self):
        theta = Parameter("theta")
        c = Circuit(1)
        c.rx(0, theta)
        c.assign_parameters({"theta": 0.5})
        assert c.is_parametric  # original untouched

    def test_inplace(self):
        theta = Parameter("theta")
        c = Circuit(1)
        c.rx(0, theta)
        out = c.assign_parameters({"theta": 0.5}, inplace=True)
        assert out is c
        assert not c.is_parametric

    def test_bind_parameters_alias(self):
        theta = Parameter("theta")
        c = Circuit(1)
        c.rx(0, theta)
        assert not c.bind_parameters({"theta": 0.5}).is_parametric

    def test_expression_evaluates_correctly(self):
        theta, phi = Parameter("theta"), Parameter("phi")
        c = Circuit(1)
        c.rx(0, theta * 2 + phi / 3)
        bound = c.assign_parameters({"theta": 1.0, "phi": 3.0})
        assert bound.opcode_list[0][3] == pytest.approx(2 * 1.0 + 3.0 / 3)


# =============================================================================
# Guards + bound simulation equivalence
# =============================================================================


class TestGuardsAndSimulation:
    def _parametric_circuit(self):
        theta = Parameter("theta")
        c = Circuit(1)
        c.rx(0, theta)
        c.measure(0)
        return c

    def test_qasm_export_rejected(self):
        with pytest.raises(CircuitTranslationError, match="unbound symbolic parameters"):
            _ = self._parametric_circuit().qasm

    def test_official_originir_rejected(self):
        with pytest.raises(CircuitTranslationError, match="unbound symbolic parameters"):
            _ = self._parametric_circuit().originir_official

    def test_simulation_rejected(self):
        with pytest.raises(ValueError, match="unbound symbolic parameters"):
            Simulator().simulate_statevector(self._parametric_circuit().originir)

    def test_bound_matches_concrete_reference(self):
        theta = Parameter("theta")
        c = Circuit(1)
        c.rx(0, theta)
        c.measure(0)
        bound = c.assign_parameters({"theta": np.pi / 2})

        ref = Circuit(1)
        ref.rx(0, np.pi / 2)
        ref.measure(0)

        sv_bound = Simulator().simulate_statevector(bound.originir)
        sv_ref = Simulator().simulate_statevector(ref.originir)
        assert np.allclose(sv_bound, sv_ref)

    def test_bound_circuit_roundtrip_then_simulate(self):
        arr = Parameters("alpha", 2)
        c = Circuit(2)
        c.ry(0, arr[0])
        c.ry(1, arr[1])
        c.measure(0, 1)
        # round-trip through text, then bind, then simulate
        parsed = Circuit.from_originir(c.originir)
        bound = parsed.assign_parameters({arr: [0.3, 0.7]})
        sv = Simulator().simulate_statevector(bound.originir)
        assert np.isclose(np.linalg.norm(sv), 1.0)
