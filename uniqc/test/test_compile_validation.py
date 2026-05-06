"""Tests for the pre-submission validation + gate-depth API.

These tests are deliberately offline (no cloud creds). They live alongside
``test_compiler.py`` and exercise the public surface that ``submit_task`` /
``submit_batch`` use to gate every cloud round-trip.
"""

from __future__ import annotations

import pytest

from uniqc import (
    Circuit,
    CompatibilityReport,
    compatibility_report,
    compute_gate_depth,
    is_compatible,
)
from uniqc.backend_adapter.backend_info import (
    BackendInfo,
    Platform,
    QubitTopology,
)


# ---------------------------------------------------------------------------
# compute_gate_depth
# ---------------------------------------------------------------------------


class TestComputeGateDepth:
    def test_empty_circuit_has_depth_zero(self):
        c = Circuit()
        assert compute_gate_depth(c) == 0

    def test_parallel_single_qubit_gates_share_a_layer(self):
        c = Circuit()
        c.h(0)
        c.h(1)
        c.h(2)
        assert compute_gate_depth(c) == 1

    def test_serial_gates_on_same_qubit(self):
        c = Circuit()
        c.h(0)
        c.x(0)
        c.h(0)
        assert compute_gate_depth(c) == 3

    def test_two_qubit_gate_uses_max_cursor_plus_one(self):
        c = Circuit()
        c.h(0)
        c.h(1)
        c.cnot(0, 1)
        assert compute_gate_depth(c) == 2

    def test_virtual_z_default_zero_depth(self):
        c = Circuit()
        c.h(0)
        c.rz(0, 0.5)
        c.h(0)
        # H, virtual RZ, H -> only 2 physical layers
        assert compute_gate_depth(c, virtual_z=True) == 2

    def test_virtual_z_disabled_counts_z(self):
        c = Circuit()
        c.h(0)
        c.rz(0, 0.5)
        c.h(0)
        assert compute_gate_depth(c, virtual_z=False) == 3

    def test_z_s_t_are_virtual(self):
        c = Circuit()
        c.h(0)
        c.z(0)
        c.s(0)
        c.t(0)
        c.h(0)
        assert compute_gate_depth(c, virtual_z=True) == 2

    def test_cz_is_not_virtual(self):
        c = Circuit()
        c.h(0)
        c.h(1)
        c.cz(0, 1)
        c.h(0)
        c.h(1)
        assert compute_gate_depth(c, virtual_z=True) == 3

    def test_measurement_does_not_add_depth(self):
        c = Circuit()
        c.h(0)
        c.measure(0)
        assert compute_gate_depth(c) == 1

    def test_barrier_synchronises_qubits(self):
        c = Circuit()
        c.h(0)            # q0 cursor=1
        c.h(1); c.h(1)    # q1 cursor=2
        c.barrier(0, 1)   # syncs q0 to cursor=2
        c.h(0)            # q0 cursor=3
        # Without barrier: depth would be max(2, 1+1) = 2.
        # With barrier:    depth is 3.
        assert compute_gate_depth(c) == 3


# ---------------------------------------------------------------------------
# Backend fixtures
# ---------------------------------------------------------------------------


def _line_backend(platform: Platform, n: int = 4, basis=("cz", "sx", "rz")) -> BackendInfo:
    topology = tuple(QubitTopology(u=i, v=i + 1) for i in range(n - 1))
    return BackendInfo(
        platform=platform,
        name="test",
        num_qubits=n,
        topology=topology,
        extra={"basis_gates": list(basis)},
    )


# ---------------------------------------------------------------------------
# compatibility_report / is_compatible
# ---------------------------------------------------------------------------


class TestCompatibilityReport:
    def test_accepts_basis_circuit(self):
        c = Circuit()
        c.sx(0)
        c.rz(0, 0.5)
        c.cz(0, 1)
        c.measure(0); c.measure(1)
        backend = _line_backend(Platform.ORIGINQ)
        report = compatibility_report(c, backend)
        assert isinstance(report, CompatibilityReport)
        assert report.compatible is True
        assert is_compatible(c, backend) is True

    def test_rejects_gate_outside_basis(self):
        c = Circuit()
        c.h(0)
        c.t(0)
        c.measure(0)
        backend = _line_backend(Platform.ORIGINQ)
        report = compatibility_report(c, backend)
        assert report.compatible is False
        assert any("basis" in e.lower() for e in report.errors)
        assert is_compatible(c, backend) is False

    def test_rejects_topology_violation(self):
        c = Circuit()
        c.cz(0, 3)  # not adjacent on a 4-qubit line
        c.measure(0); c.measure(3)
        backend = _line_backend(Platform.ORIGINQ)
        report = compatibility_report(c, backend)
        assert report.compatible is False
        assert any("topology" in e.lower() or "edge" in e.lower() for e in report.errors)

    def test_rejects_too_many_qubits(self):
        c = Circuit()
        c.h(0); c.h(7)
        c.measure(0); c.measure(7)
        backend = _line_backend(Platform.ORIGINQ, n=4)
        report = compatibility_report(c, backend)
        assert report.compatible is False
        assert any("qubit" in e.lower() for e in report.errors)

    def test_no_backend_returns_warning_only(self):
        c = Circuit()
        c.h(0); c.cnot(0, 1); c.measure(0); c.measure(1)
        report = compatibility_report(c, None)
        assert report.compatible is True
        assert report.warnings  # should warn about missing backend info
        assert report.gate_depth == 2

    def test_report_carries_used_gates_and_qubits(self):
        c = Circuit()
        c.h(0); c.cnot(0, 1); c.measure(0); c.measure(1)
        report = compatibility_report(c, None)
        assert "H" in report.used_gates
        assert "CNOT" in report.used_gates
        assert report.used_qubits == {0, 1}

    def test_explicit_basis_overrides_backend(self):
        c = Circuit()
        c.h(0); c.measure(0)
        backend = _line_backend(Platform.ORIGINQ)
        # When caller pins basis to {h}, the H circuit becomes acceptable.
        report = compatibility_report(c, backend, basis_gates=("h",))
        assert report.compatible is True
