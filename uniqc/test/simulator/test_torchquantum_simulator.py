"""Tests for TorchQuantum simulator backend."""

from __future__ import annotations

import numpy as np
import pytest

torchquantum = pytest.importorskip("torchquantum", reason="torchquantum not installed")

import torch

from uniqc.circuit_builder import Circuit
from uniqc.simulator import Simulator
from uniqc.simulator.torchquantum_simulator import TORCHQUANTUM_AVAILABLE, TorchQuantumSimulator


@pytest.fixture
def cpp_sim():
    return Simulator(backend_type="statevector")


class TestGateMapping:
    """Test that TorchQuantum gates produce correct statevectors."""

    def _compare(self, circuit, cpp_sim):
        sim = TorchQuantumSimulator()
        tq_sv = sim.simulate_statevector(circuit.opcode_list).detach().numpy()
        cpp_sv = cpp_sim.simulate_statevector(circuit.originir)
        np.testing.assert_allclose(tq_sv, cpp_sv, atol=1e-5)

    def test_hadamard(self, cpp_sim):
        c = Circuit(1)
        c.h(0)
        self._compare(c, cpp_sim)

    def test_x_gate(self, cpp_sim):
        c = Circuit(1)
        c.x(0)
        self._compare(c, cpp_sim)

    def test_rx_gate(self, cpp_sim):
        c = Circuit(1)
        c.rx(0, 1.23)
        self._compare(c, cpp_sim)

    def test_ry_gate(self, cpp_sim):
        c = Circuit(1)
        c.ry(0, 0.77)
        self._compare(c, cpp_sim)

    def test_rz_gate(self, cpp_sim):
        c = Circuit(1)
        c.rz(0, 2.5)
        self._compare(c, cpp_sim)

    def test_cnot(self, cpp_sim):
        c = Circuit(2)
        c.h(0)
        c.cx(0, 1)
        self._compare(c, cpp_sim)

    def test_bell_state(self, cpp_sim):
        c = Circuit(2)
        c.h(0)
        c.cnot(0, 1)
        sim = TorchQuantumSimulator()
        tq_sv = sim.simulate_statevector(c.opcode_list).detach().numpy()
        cpp_sv = cpp_sim.simulate_statevector(c.originir)
        expected = np.array([1 / np.sqrt(2), 0, 0, 1 / np.sqrt(2)])
        np.testing.assert_allclose(np.abs(tq_sv), np.abs(expected), atol=1e-5)
        np.testing.assert_allclose(tq_sv, cpp_sv, atol=1e-5)

    def test_cz_gate(self, cpp_sim):
        c = Circuit(2)
        c.h(0)
        c.h(1)
        c.cz(0, 1)
        self._compare(c, cpp_sim)

    def test_swap_gate(self, cpp_sim):
        c = Circuit(2)
        c.x(0)
        c.swap(0, 1)
        self._compare(c, cpp_sim)

    def test_multi_gate_circuit(self, cpp_sim):
        c = Circuit(2)
        c.h(0)
        c.rx(1, 0.5)
        c.cnot(0, 1)
        c.ry(0, 1.2)
        c.rz(1, 0.3)
        self._compare(c, cpp_sim)


class TestParamOverrides:
    """Test parameter injection with torch.Tensor."""

    def test_param_injection_basic(self):
        sim = TorchQuantumSimulator()
        c = Circuit(1)
        c.rx(0, 0.0)

        theta = torch.tensor([torch.pi], requires_grad=True)
        param_overrides = {0: theta.unsqueeze(0)}

        sv = sim.simulate_statevector(c.opcode_list, param_overrides)
        assert sv.shape == (2,)
        assert abs(sv[0].item()) < 1e-4
        assert abs(abs(sv[1].item()) - 1.0) < 1e-4

    def test_gradient_flows(self):
        sim = TorchQuantumSimulator()
        c = Circuit(1)
        c.rz(0, 0.0)

        theta = torch.tensor([0.5], requires_grad=True)
        param_overrides = {0: theta.unsqueeze(0)}

        sv = sim.simulate_statevector(c.opcode_list, param_overrides)
        loss = sv[0].abs().square().sum()
        loss.backward()

        assert theta.grad is not None
        assert not torch.isnan(theta.grad).any()
        assert not torch.isinf(theta.grad).any()

    def test_multi_param_gradient(self):
        sim = TorchQuantumSimulator()
        c = Circuit(2)
        c.ry(0, 0.0)
        c.ry(1, 0.0)

        params = torch.tensor([0.5, 0.3], requires_grad=True)
        param_overrides = {
            0: params[0].unsqueeze(0).unsqueeze(0),
            1: params[1].unsqueeze(0).unsqueeze(0),
        }

        sv = sim.simulate_statevector(c.opcode_list, param_overrides)
        loss = sv.abs().square().sum()
        loss.backward()

        assert params.grad is not None
        assert params.grad.shape == (2,)


class TestExpectation:
    """Test expectation value computation."""

    def test_z_expectation_zero_state(self):
        sim = TorchQuantumSimulator()
        c = Circuit(1)
        expval = sim.expectation(c.opcode_list, [("Z", 1.0)]).item()
        assert abs(expval - 1.0) < 1e-5

    def test_z_expectation_one_state(self):
        sim = TorchQuantumSimulator()
        c = Circuit(1)
        c.x(0)
        expval = sim.expectation(c.opcode_list, [("Z", 1.0)]).item()
        assert abs(expval - (-1.0)) < 1e-5

    def test_zz_expectation_bell_state(self):
        sim = TorchQuantumSimulator()
        c = Circuit(2)
        c.h(0)
        c.cnot(0, 1)
        expval = sim.expectation(c.opcode_list, [("ZZ", 1.0)]).item()
        assert abs(expval - 1.0) < 1e-5

    def test_expectation_differentiable(self):
        sim = TorchQuantumSimulator()
        c = Circuit(1)
        c.ry(0, 0.0)

        theta = torch.tensor([0.5], requires_grad=True)
        param_overrides = {0: theta.unsqueeze(0).unsqueeze(0)}

        expval = sim.expectation(c.opcode_list, [("Z", 1.0)], param_overrides)
        expval.backward()
        assert theta.grad is not None
        expected_grad = -torch.sin(torch.tensor(0.5))
        assert abs(theta.grad.item() - expected_grad.item()) < 1e-3

    def test_hamiltonian_with_identity(self):
        sim = TorchQuantumSimulator()
        c = Circuit(1)
        c.h(0)
        expval = sim.expectation(c.opcode_list, [("I", 2.0), ("X", 1.0)]).item()
        assert abs(expval - 3.0) < 1e-5

    def test_x_expectation_plus_state(self):
        sim = TorchQuantumSimulator()
        c = Circuit(1)
        c.h(0)
        expval = sim.expectation(c.opcode_list, [("X", 1.0)]).item()
        assert abs(expval - 1.0) < 1e-5


class TestAvailability:
    def test_available_flag(self):
        assert isinstance(TORCHQUANTUM_AVAILABLE, bool)
