"""IBM adapter tests using qiskit's fake backend providers.

These tests exercise ``IBMCircuitAdapter.adapt()`` against locally-available
fake backends (no IBM Quantum credentials required).
"""

from __future__ import annotations

import pytest

from uniqc import Circuit

pytestmark = pytest.mark.requires_qiskit


def _has_fake_provider() -> bool:
    try:
        from qiskit.providers.fake_provider import GenericBackendV2  # noqa: F401

        return True
    except ImportError:
        return False


requires_fake_provider = pytest.mark.skipif(
    not _has_fake_provider(),
    reason="qiskit fake provider not available",
)


def _all_gates_circuit() -> Circuit:
    """Circuit targeting all gates in the universal gate set."""
    c = Circuit(4)
    # 1q parametric
    c.rx(0, 0.1)
    c.ry(0, 0.2)
    c.rz(0, 0.3)
    c.p(0, 0.4)
    c.u1(0, 0.5)
    c.u2(0, 0.6, 0.7)
    c.u3(0, 0.8, 0.9, 1.0)
    # 1q non-parametric
    c.h(0)
    c.x(0)
    c.y(0)
    c.z(0)
    c.s(0)
    c.t(0)
    # 2q non-parametric
    c.cnot(0, 1)
    c.cz(0, 1)
    c.swap(0, 1)
    # 2q parametric
    c.crx(0, 1, 0.5)
    c.cry(0, 1, 0.6)
    c.crz(0, 1, 0.7)
    c.cp(0, 1, 0.8)
    c.cu(0, 1, 0.9, 1.0, 1.1)
    # 3q
    c.toffoli(0, 1, 2)
    return c


# ---------------------------------------------------------------------------
# IBMCircuitAdapter.adapt() tests
# ---------------------------------------------------------------------------


@requires_fake_provider
class TestIBMCircuitAdapter:
    """Test that IBMCircuitAdapter produces valid qiskit QuantumCircuit objects."""

    @pytest.fixture
    def adapter(self):
        from uniqc.backend_adapter.circuit_adapter import IBMCircuitAdapter

        return IBMCircuitAdapter()

    def test_adapt_simple_circuit(self, adapter):
        """A minimal H+CNOT circuit converts to a valid qiskit QuantumCircuit."""
        from qiskit import QuantumCircuit as QiskitQC

        c = Circuit(2)
        c.h(0)
        c.cnot(0, 1)
        c.measure(0, 1)

        qiskit_circ = adapter.adapt(c)
        assert isinstance(qiskit_circ, QiskitQC)
        assert qiskit_circ.num_qubits >= 2

    def test_adapt_all_target_gates(self, adapter):
        """All gates in the universal set convert without error."""
        c = _all_gates_circuit()
        qiskit_circ = adapter.adapt(c)
        assert qiskit_circ is not None

    def test_adapt_preserves_qubit_count(self, adapter):
        c = Circuit(3)
        c.h(0)
        c.cnot(0, 1)
        c.cnot(1, 2)
        c.measure(0, 1, 2)

        qiskit_circ = adapter.adapt(c)
        assert qiskit_circ.num_qubits >= 3


# ---------------------------------------------------------------------------
# QiskitAdapter query() status normalization
# ---------------------------------------------------------------------------


@requires_fake_provider
class TestQiskitStatusNormalization:
    """Verify _normalize_qiskit_status maps correctly."""

    def test_normalize_done(self):
        from uniqc.backend_adapter.task.adapters.qiskit_adapter import _normalize_qiskit_status

        assert _normalize_qiskit_status("DONE") == "success"
        assert _normalize_qiskit_status("COMPLETED") == "success"

    def test_normalize_failed(self):
        from uniqc.backend_adapter.task.adapters.qiskit_adapter import _normalize_qiskit_status

        for name in ("ERROR", "CANCELLED", "FAILED"):
            assert _normalize_qiskit_status(name) == "failed"

    def test_normalize_running(self):
        from uniqc.backend_adapter.task.adapters.qiskit_adapter import _normalize_qiskit_status

        for name in ("INITIALIZING", "QUEUED", "VALIDATING", "RUNNING", "EXECUTING"):
            assert _normalize_qiskit_status(name) == "running"
