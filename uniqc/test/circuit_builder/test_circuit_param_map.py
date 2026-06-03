"""Tests for Circuit.param_map — tensor parameter support for differentiable circuits."""

import pytest

from uniqc.circuit_builder.qcircuit import Circuit


# =============================================================================
# TestParamMapBasics
# =============================================================================


class TestParamMapBasics:
    """Basic param_map lifecycle tests."""

    def test_param_map_starts_empty(self):
        c = Circuit()
        assert c.param_map == {}
        assert c.has_tensor_params() is False
        assert c.tensor_params == []

    def test_set_param_basic(self):
        c = Circuit()
        c.rx(0, 0.0)
        sentinel = object()
        c.set_param(0, sentinel)
        assert c.get_param(0) is sentinel
        assert c.has_tensor_params() is True

    def test_set_param_out_of_range_raises(self):
        c = Circuit()
        c.rx(0, 0.0)
        with pytest.raises(IndexError, match="out of range"):
            c.set_param(1, object())
        with pytest.raises(IndexError, match="out of range"):
            c.set_param(-1, object())

    def test_set_param_empty_circuit_raises(self):
        c = Circuit()
        with pytest.raises(IndexError, match="out of range"):
            c.set_param(0, object())

    def test_get_param_missing_raises(self):
        c = Circuit()
        c.rx(0, 0.0)
        with pytest.raises(KeyError):
            c.get_param(0)

    def test_set_param_last(self):
        c = Circuit()
        c.h(0)
        c.rx(0, 0.0)
        sentinel = object()
        idx = c.set_param_last(sentinel)
        assert idx == 1
        assert c.get_param(1) is sentinel

    def test_set_param_last_empty_circuit_raises(self):
        c = Circuit()
        with pytest.raises(IndexError, match="out of range"):
            c.set_param_last(object())

    def test_tensor_params_returns_all(self):
        c = Circuit()
        c.rx(0, 0.0)
        c.ry(0, 0.0)
        c.rz(0, 0.0)
        a, b, d = object(), object(), object()
        c.set_param(0, a)
        c.set_param(1, b)
        c.set_param(2, d)
        params = c.tensor_params
        # dict preserves insertion order (Python 3.7+)
        assert params == [a, b, d]

    def test_multiple_params_independent(self):
        c = Circuit()
        c.rx(0, 0.0)
        c.rx(1, 0.0)
        a, b = "param_a", "param_b"
        c.set_param(0, a)
        c.set_param(1, b)
        assert c.get_param(0) is a
        assert c.get_param(1) is b
        assert len(c.param_map) == 2


# =============================================================================
# TestCopy
# =============================================================================


class TestCopy:
    """Tests for copy() interaction with param_map."""

    def test_copy_preserves_param_map(self):
        c = Circuit()
        c.rx(0, 0.0)
        c.ry(0, 0.0)
        sentinel = object()
        c.set_param(0, sentinel)
        c2 = c.copy()
        assert c2.has_tensor_params()
        assert c2.get_param(0) is sentinel

    def test_copy_shares_tensor_ref(self):
        c = Circuit()
        c.rx(0, 0.0)
        sentinel = object()
        c.set_param(0, sentinel)
        c2 = c.copy()
        # Same object — shared reference by design
        assert c2.get_param(0) is sentinel
        assert c.get_param(0) is c2.get_param(0)

    def test_copy_independent_map_mutation(self):
        c = Circuit()
        c.rx(0, 0.0)
        c.ry(0, 0.0)
        c.set_param(0, "a")
        c2 = c.copy()
        c2.set_param(1, "b")
        # Original unaffected
        assert 1 not in c.param_map
        assert len(c.param_map) == 1
        assert len(c2.param_map) == 2

    def test_copy_without_param_map(self):
        c = Circuit()
        c.h(0)
        c2 = c.copy()
        assert c2.param_map == {}

    def test_copy_preserves_multiple_params(self):
        c = Circuit()
        c.rx(0, 0.0)
        c.ry(0, 0.0)
        c.rz(0, 0.0)
        c.set_param(0, "a")
        c.set_param(1, "b")
        c.set_param(2, "d")
        c2 = c.copy()
        assert c2.tensor_params == ["a", "b", "d"]


# =============================================================================
# TestSerializationNotAffected
# =============================================================================


class TestSerializationNotAffected:
    """param_map must not alter OriginIR / QASM output."""

    def test_originir_unchanged_with_param_map(self):
        c1 = Circuit()
        c1.rx(0, 0.5)
        originir_base = c1.originir

        c2 = Circuit()
        c2.rx(0, 0.5)
        c2.set_param(0, object())
        assert c2.originir == originir_base

    def test_qasm_unchanged_with_param_map(self):
        c1 = Circuit()
        c1.rx(0, 0.5)
        qasm_base = c1.qasm

        c2 = Circuit()
        c2.rx(0, 0.5)
        c2.set_param(0, object())
        assert c2.qasm == qasm_base


# =============================================================================
# TestControlDaggerContext
# =============================================================================


class TestControlDaggerContext:
    """param_map works correctly with control / dagger contexts."""

    def test_param_map_with_control_context(self):
        c = Circuit()
        with c.control(0):
            c.rx(1, 0.0)
        # The controlled RX is at index 0
        sentinel = object()
        c.set_param(0, sentinel)
        assert c.get_param(0) is sentinel

    def test_param_map_with_dagger_context(self):
        c = Circuit()
        with c.dagger():
            c.rx(0, 0.0)
        sentinel = object()
        c.set_param_last(sentinel)
        assert c.get_param(0) is sentinel

    def test_param_map_index_matches_gate_position(self):
        c = Circuit()
        c.h(0)            # idx 0
        c.rx(0, 0.0)      # idx 1
        with c.control(0):
            c.ry(1, 0.0)  # idx 2
        c.rz(0, 0.0)      # idx 3

        c.set_param(1, "rx_param")
        c.set_param(2, "ry_param")
        c.set_param(3, "rz_param")

        assert c.get_param(1) == "rx_param"
        assert c.get_param(2) == "ry_param"
        assert c.get_param(3) == "rz_param"
        assert len(c.param_map) == 3


# =============================================================================
# TestWithTorch (requires torch)
# =============================================================================


class TestWithTorch:
    """Tests using actual torch.Tensor / nn.Parameter."""

    @pytest.fixture(autouse=True)
    def _require_torch(self):
        torch = pytest.importorskip("torch")
        self.torch = torch

    def test_set_param_with_tensor(self):
        torch = self.torch
        c = Circuit()
        c.rx(0, 0.0)
        t = torch.tensor(0.5, requires_grad=True)
        c.set_param(0, t)
        assert c.get_param(0) is t
        assert c.get_param(0).requires_grad

    def test_set_param_with_nn_parameter(self):
        torch = self.torch
        c = Circuit()
        c.rx(0, 0.0)
        c.ry(0, 0.0)
        p = torch.nn.Parameter(torch.randn(2))
        c.set_param(0, p[0])
        c.set_param(1, p[1])
        assert c.has_tensor_params()
        assert len(c.tensor_params) == 2

    def test_tensor_params_with_leaf_tensors(self):
        torch = self.torch
        c = Circuit()
        c.rx(0, 0.0)
        c.ry(0, 0.0)
        t0 = torch.tensor(0.1, requires_grad=True)
        t1 = torch.tensor(0.2, requires_grad=True)
        c.set_param(0, t0)
        c.set_param(1, t1)
        # leaf tensors work directly with optimizer
        optimizer = torch.optim.Adam(c.tensor_params, lr=0.01)
        assert optimizer is not None

    def test_copy_preserves_nn_parameter(self):
        torch = self.torch
        c = Circuit()
        c.rx(0, 0.0)
        p = torch.nn.Parameter(torch.tensor(0.5))
        c.set_param(0, p)
        c2 = c.copy()
        assert c2.get_param(0) is p

    def test_parametric_circuit_flow(self):
        """Simulate the HEA-style param registration pattern."""
        torch = self.torch
        n_qubits = 2
        depth = 1

        c = Circuit(n_qubits)
        all_params = torch.nn.Parameter(torch.randn(2 * n_qubits * depth) * 0.1)
        idx = 0
        for _ in range(depth):
            for q in range(n_qubits):
                c.rz(q, 0.0)
                c.set_param_last(all_params[idx])
                idx += 1
                c.ry(q, 0.0)
                c.set_param_last(all_params[idx])
                idx += 1
            for i in range(n_qubits):
                c.cnot(i, (i + 1) % n_qubits)

        assert c.has_tensor_params()
        assert len(c.param_map) == 2 * n_qubits * depth
        # All tensor_params should be slices of the same nn.Parameter
        assert all(isinstance(p, torch.Tensor) for p in c.tensor_params)
        # CNOT gates have no tensor params
        cnot_indices = [
            i for i, op in enumerate(c.opcode_list) if op[0] == "CNOT"
        ]
        for ci in cnot_indices:
            assert ci not in c.param_map

    def test_gradient_flows_through_param_map(self):
        """Verify autograd works end-to-end with param_map tensors."""
        torch = self.torch
        c = Circuit(1)
        c.ry(0, 0.0)
        theta = torch.tensor(0.5, requires_grad=True)
        c.set_param(0, theta)
        # Forward: <Z> = cos(theta)
        expectation = torch.cos(theta)
        expectation.backward()
        # d(cos(theta))/d(theta) = -sin(theta)
        expected_grad = -torch.sin(torch.tensor(0.5))
        assert abs(theta.grad.item() - expected_grad.item()) < 1e-6

    def test_optimizer_step_updates_tensor(self):
        """Verify optimizer step modifies the tensor stored in param_map."""
        torch = self.torch
        c = Circuit(1)
        c.ry(0, 0.0)
        theta = torch.tensor(1.0, requires_grad=True)
        c.set_param(0, theta)
        original = theta.item()
        opt = torch.optim.SGD([theta], lr=0.1)
        opt.zero_grad()
        torch.cos(theta).backward()
        opt.step()
        assert theta.item() != original
