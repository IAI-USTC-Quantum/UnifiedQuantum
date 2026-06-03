"""Tests for the backend-agnostic expectation() function."""

import math

import pytest
import torch

from uniqc.circuit_builder.qcircuit import Circuit
from uniqc.torch_adapter.expectation import expectation


# =============================================================================
# Gate-level correctness (single-qubit gates on |0⟩)
# =============================================================================


class TestGateCorrectness:
    """Verify gate matrices by checking expectation values on known states."""

    def _run(self, circuit, hamiltonian, n_qubits, pm=None):
        return expectation(circuit, hamiltonian, param_map=pm or {}, backend="virtual").item()

    def test_identity(self):
        """|0⟩ under I → ⟨Z⟩ = 1"""
        c = Circuit(1)
        c.identity(0)
        assert abs(self._run(c, [("Z", 1.0)], 1) - 1.0) < 1e-6

    def test_x_gate(self):
        """X|0⟩ = |1⟩ → ⟨Z⟩ = -1"""
        c = Circuit(1)
        c.x(0)
        assert abs(self._run(c, [("Z", 1.0)], 1) - (-1.0)) < 1e-6

    def test_y_gate(self):
        """Y|0⟩ = i|1⟩ → ⟨Z⟩ = -1"""
        c = Circuit(1)
        c.y(0)
        assert abs(self._run(c, [("Z", 1.0)], 1) - (-1.0)) < 1e-6

    def test_z_gate(self):
        """Z|0⟩ = |0⟩ → ⟨Z⟩ = 1"""
        c = Circuit(1)
        c.z(0)
        assert abs(self._run(c, [("Z", 1.0)], 1) - 1.0) < 1e-6

    def test_h_gate(self):
        """H|0⟩ = |+⟩ → ⟨Z⟩ = 0, ⟨X⟩ = 1"""
        c = Circuit(1)
        c.h(0)
        assert abs(self._run(c, [("Z", 1.0)], 1)) < 1e-6
        assert abs(self._run(c, [("X", 1.0)], 1) - 1.0) < 1e-6

    def test_s_gate(self):
        """S|+⟩ → ⟨Y⟩ = 1"""
        c = Circuit(1)
        c.h(0)
        c.s(0)
        assert abs(self._run(c, [("Y", 1.0)], 1) - 1.0) < 1e-6

    def test_rx_pi(self):
        """RX(π)|0⟩ = -i|1⟩ → ⟨Z⟩ = -1"""
        c = Circuit(1)
        c.rx(0, math.pi)
        assert abs(self._run(c, [("Z", 1.0)], 1) - (-1.0)) < 1e-5

    def test_ry_pi_half(self):
        """RY(π/2)|0⟩ = (|0⟩ + |1⟩)/√2 → ⟨Z⟩ = 0, ⟨X⟩ = 1"""
        c = Circuit(1)
        c.ry(0, math.pi / 2)
        assert abs(self._run(c, [("Z", 1.0)], 1)) < 1e-5
        assert abs(self._run(c, [("X", 1.0)], 1) - 1.0) < 1e-5

    def test_rz_on_zero(self):
        """RZ(θ)|0⟩ = e^{-iθ/2}|0⟩ → ⟨Z⟩ = 1 (global phase)"""
        c = Circuit(1)
        c.rz(0, 1.23)
        assert abs(self._run(c, [("Z", 1.0)], 1) - 1.0) < 1e-5

    def test_cnot(self):
        """CNOT|00⟩ = |00⟩ → ⟨Z₀Z₁⟩ = 1"""
        c = Circuit(2)
        c.cnot(0, 1)
        assert abs(self._run(c, [("ZZ", 1.0)], 2) - 1.0) < 1e-6

    def test_cnot_flips_target(self):
        """X₀CNOT|00⟩ = |11⟩ → ⟨Z₀⟩ = -1, ⟨Z₁⟩ = -1"""
        c = Circuit(2)
        c.x(0)
        c.cnot(0, 1)
        assert abs(self._run(c, [("ZI", 1.0)], 2) - (-1.0)) < 1e-6
        assert abs(self._run(c, [("IZ", 1.0)], 2) - (-1.0)) < 1e-6

    def test_swap(self):
        """SWAP|01⟩ = |10⟩ → ⟨Z₀⟩ = 1, ⟨Z₁⟩ = -1

        uniqc LSB: |01⟩ means qubit 0=1, qubit 1=0.
        After SWAP: qubit 0=0, qubit 1=1 → ⟨IZ⟩(qubit 0) = 1, ⟨ZI⟩(qubit 1) = -1.
        """
        c = Circuit(2)
        c.x(1)
        c.swap(0, 1)
        # "IZ" = I on qubit 1, Z on qubit 0 → ⟨Z₀⟩ = 1
        assert abs(self._run(c, [("IZ", 1.0)], 2) - 1.0) < 1e-6
        # "ZI" = Z on qubit 1, I on qubit 0 → ⟨Z₁⟩ = -1
        assert abs(self._run(c, [("ZI", 1.0)], 2) - (-1.0)) < 1e-6

    def test_toffoli(self):
        """TOFFOLI|110⟩ = |111⟩ → ⟨Z₂⟩ = -1"""
        c = Circuit(3)
        c.x(0)
        c.x(1)
        c.toffoli(0, 1, 2)
        assert abs(self._run(c, [("IIZ", 1.0)], 3) - (-1.0)) < 1e-6

    def test_toffoli_no_flip(self):
        """TOFFOLI|100⟩ = |100⟩ → ⟨Z₂⟩ = 1"""
        c = Circuit(3)
        c.x(0)
        c.toffoli(0, 1, 2)
        assert abs(self._run(c, [("IIZ", 1.0)], 3) - 1.0) < 1e-6

    def test_u3_as_ry(self):
        """U3(θ,0,0) = RY(θ) → same ⟨Z⟩"""
        theta = 0.7
        c1 = Circuit(1)
        c1.ry(0, theta)
        c2 = Circuit(1)
        c2.u3(0, theta, 0, 0)
        v1 = self._run(c1, [("Z", 1.0)], 1)
        v2 = self._run(c2, [("Z", 1.0)], 1)
        assert abs(v1 - v2) < 1e-5

    def test_rxx_entanglement(self):
        """RXX(π)|00⟩ = -i|11⟩ → ⟨ZZ⟩ = +1 (Z|1⟩ = -|1⟩, (-1)·(-1) = +1)"""
        c = Circuit(2)
        c.xx(0, 1, math.pi)
        assert abs(self._run(c, [("ZZ", 1.0)], 2) - 1.0) < 1e-5

    def test_rzz_on_plus_state(self):
        """RZZ(π/2)|++⟩ — verify ⟨ZZ⟩ is real and correct"""
        c = Circuit(2)
        c.h(0)
        c.h(1)
        c.zz(0, 1, math.pi / 2)
        # RZZ(π/2)|++⟩ = e^{-iπ/4 Z⊗Z}|++⟩
        # ⟨ZZ⟩ = Re⟨ψ|ZZ|ψ⟩ = 0 (imaginary eigenvalue)
        val = self._run(c, [("ZZ", 1.0)], 2)
        assert abs(val) < 1e-5


# =============================================================================
# Gradient correctness
# =============================================================================


class TestGradientFlow:
    """Verify gradients flow correctly through the virtual backend."""

    def test_dz_dry_theta(self):
        """d⟨Z⟩/dθ for RY(θ)|0⟩ = -sin(θ)"""
        c = Circuit(1)
        c.ry(0, 0.0)
        theta = torch.tensor(0.5, requires_grad=True)
        expval = expectation(c, [("Z", 1.0)], param_map={0: theta})
        expval.backward()
        expected = -torch.sin(theta)
        assert abs(theta.grad.item() - expected.item()) < 1e-5

    def test_gradient_at_zero(self):
        """d⟨Z⟩/dθ at θ=0 should be 0 (extremum of cos)"""
        c = Circuit(1)
        c.ry(0, 0.0)
        theta = torch.tensor(0.0, requires_grad=True)
        expval = expectation(c, [("Z", 1.0)], param_map={0: theta})
        expval.backward()
        assert abs(theta.grad.item()) < 1e-6

    def test_gradient_at_pi_half(self):
        """d⟨Z⟩/dθ at θ=π/2 should be -1"""
        c = Circuit(1)
        c.ry(0, 0.0)
        theta = torch.tensor(math.pi / 2, requires_grad=True)
        expval = expectation(c, [("Z", 1.0)], param_map={0: theta})
        expval.backward()
        assert abs(theta.grad.item() - (-1.0)) < 1e-5

    def test_multi_param_gradient(self):
        """Gradients w.r.t. two independent RY angles."""
        c = Circuit(2)
        c.ry(0, 0.0)
        c.ry(1, 0.0)
        t0 = torch.tensor(0.3, requires_grad=True)
        t1 = torch.tensor(0.7, requires_grad=True)
        expval = expectation(c, [("ZI", 1.0)], param_map={0: t0, 1: t1})
        expval.backward()
        # ⟨ZI⟩ = cos(t0), so d/dt0 = -sin(t0), d/dt1 = 0
        assert abs(t0.grad.item() - (-math.sin(0.3))) < 1e-5
        assert abs(t1.grad.item()) < 1e-5

    def test_two_qubit_hamiltonian_gradient(self):
        """Gradient through ZZ Hamiltonian."""
        c = Circuit(2)
        c.ry(0, 0.0)
        c.ry(1, 0.0)
        c.cnot(0, 1)
        t0 = torch.tensor(0.5, requires_grad=True)
        t1 = torch.tensor(0.3, requires_grad=True)
        expval = expectation(c, [("ZZ", 1.0)], param_map={0: t0, 1: t1})
        expval.backward()
        # Just verify gradients exist and are finite
        assert t0.grad is not None and torch.isfinite(t0.grad)
        assert t1.grad is not None and torch.isfinite(t1.grad)

    def test_nn_parameter_integration(self):
        """Full optimizer step with nn.Parameter via param_map."""
        c = Circuit(1)
        c.ry(0, 0.0)
        params = torch.nn.Parameter(torch.tensor([1.0]))
        opt = torch.optim.SGD([params], lr=0.1)
        original = params.item()
        opt.zero_grad()
        expval = expectation(c, [("Z", 1.0)], param_map={0: params[0]})
        expval.backward()
        opt.step()
        assert params.item() != original


# =============================================================================
# Hamiltonian accumulation
# =============================================================================


class TestHamiltonianAccumulation:
    """Verify multi-term Hamiltonian is accumulated correctly."""

    def test_multi_pauli_terms(self):
        """H = 0.5*Z + 0.5*X on |0⟩: ⟨H⟩ = 0.5*1 + 0.5*0 = 0.5"""
        c = Circuit(1)
        val = expectation(c, [("Z", 0.5), ("X", 0.5)], backend="virtual").item()
        assert abs(val - 0.5) < 1e-6

    def test_identity_term(self):
        """Identity terms contribute their coefficient directly."""
        c = Circuit(1)
        val = expectation(c, [("I", 2.0), ("Z", 0.5)], backend="virtual").item()
        assert abs(val - 2.5) < 1e-6

    def test_skips_zero_coefficient(self):
        """Terms with ~0 coefficient are skipped."""
        c = Circuit(1)
        val = expectation(c, [("Z", 1.0), ("X", 1e-16)], backend="virtual").item()
        assert abs(val - 1.0) < 1e-6


# =============================================================================
# param_map from circuit
# =============================================================================


class TestCircuitParamMap:
    """Verify param_map is read from circuit when not passed explicitly."""

    def test_uses_circuit_param_map(self):
        c = Circuit(1)
        c.ry(0, 0.0)
        theta = torch.tensor(0.5, requires_grad=True)
        c.set_param(0, theta)
        expval = expectation(c, [("Z", 1.0)])
        expval.backward()
        assert abs(theta.grad.item() - (-math.sin(0.5))) < 1e-5

    def test_explicit_overrides_circuit(self):
        c = Circuit(1)
        c.ry(0, 0.0)
        c.set_param(0, torch.tensor(0.0))  # circuit param = 0
        override = torch.tensor(0.5, requires_grad=True)
        expval = expectation(c, [("Z", 1.0)], param_map={0: override})
        expval.backward()
        assert abs(override.grad.item() - (-math.sin(0.5))) < 1e-5


# =============================================================================
# Backend routing
# =============================================================================


class TestBackendRouting:
    """Verify backend parameter works correctly."""

    def test_virtual_backend(self):
        c = Circuit(1)
        c.x(0)
        val = expectation(c, [("Z", 1.0)], backend="virtual").item()
        assert abs(val - (-1.0)) < 1e-6

    def test_unknown_backend_raises(self):
        c = Circuit(1)
        with pytest.raises(ValueError, match="Unknown expectation backend"):
            expectation(c, [("Z", 1.0)], backend="nonexistent")

    def test_backend_normalization(self):
        """Backend names are case-insensitive and normalize hyphens."""
        c = Circuit(1)
        c.x(0)
        val = expectation(c, [("Z", 1.0)], backend="Virtual").item()
        assert abs(val - (-1.0)) < 1e-6


# =============================================================================
# HEA-style training flow
# =============================================================================


class TestHEATrainingFlow:
    """End-to-end test with HEA-style parametric circuit."""

    def test_hea_convergence(self):
        """VQE-style: minimize ⟨H⟩ with HEA ansatz."""
        n_qubits = 2
        depth = 2
        n_params = 2 * n_qubits * depth

        c = Circuit(n_qubits)
        params = torch.nn.Parameter(torch.randn(n_params) * 0.1)
        idx = 0
        for _ in range(depth):
            for q in range(n_qubits):
                c.rz(q, 0.0)
                c.set_param_last(params[idx]); idx += 1
                c.ry(q, 0.0)
                c.set_param_last(params[idx]); idx += 1
            for q in range(n_qubits):
                c.cnot(q, (q + 1) % n_qubits)

        hamiltonian = [("ZZ", 1.0), ("ZI", -0.5), ("IZ", -0.5)]
        opt = torch.optim.Adam([params], lr=0.05)

        energies = []
        for _ in range(60):
            opt.zero_grad()
            e = expectation(c, hamiltonian)
            e.backward()
            opt.step()
            energies.append(e.item())

        # Should converge (final energy < initial energy)
        assert energies[-1] < energies[0]
        # Ground state of ZZ - 0.5*ZI - 0.5*IZ is -1.5
        assert energies[-1] < -0.5

    def test_gradient_shapes(self):
        """Gradients have correct shape for multi-param circuit."""
        c = Circuit(2)
        c.ry(0, 0.0)
        c.ry(1, 0.0)
        c.cnot(0, 1)
        t0 = torch.tensor(0.5, requires_grad=True)
        t1 = torch.tensor(0.3, requires_grad=True)
        expval = expectation(c, [("ZZ", 1.0)], param_map={0: t0, 1: t1})
        expval.backward()
        assert t0.grad.shape == ()
        assert t1.grad.shape == ()
