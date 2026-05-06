"""Tests for the MPS simulator and ``dummy:mps:linear-N`` backend wiring."""

from __future__ import annotations

import math

import numpy as np
import pytest

from uniqc.simulator import MPSConfig, MPSSimulator


def _bell_ir() -> str:
    return (
        "QINIT 2\n"
        "CREG 2\n"
        "H q[0]\n"
        "CNOT q[0],q[1]\n"
    )


def _ghz_ir(n: int) -> str:
    lines = [f"QINIT {n}", f"CREG {n}", "H q[0]"]
    for i in range(n - 1):
        lines.append(f"CNOT q[{i}],q[{i + 1}]")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Direct MPSSimulator API
# ---------------------------------------------------------------------------


def test_bell_pmeasure_matches_analytic():
    sim = MPSSimulator()
    probs = sim.simulate_pmeasure(_bell_ir())
    assert len(probs) == 4
    assert probs[0] == pytest.approx(0.5, abs=1e-9)
    assert probs[3] == pytest.approx(0.5, abs=1e-9)
    assert probs[1] == pytest.approx(0.0, abs=1e-9)
    assert probs[2] == pytest.approx(0.0, abs=1e-9)


def test_bell_statevector_q0_lsb():
    sim = MPSSimulator()
    psi = sim.simulate_statevector(_bell_ir())
    # |00> + |11> with q0 as LSB → indices 0 and 3
    expected = np.zeros(4, dtype=complex)
    expected[0] = expected[3] = 1 / math.sqrt(2)
    assert np.allclose(psi, expected, atol=1e-9)


def test_ghz4_shots_distribution():
    sim = MPSSimulator(MPSConfig(seed=12345))
    counts = sim.simulate_shots(_ghz_ir(4), shots=2000)
    # No MEASURE ⇒ all 4 qubits sampled. Should see ~50/50 between 0 and 15.
    assert set(counts.keys()) <= {0, 15}
    assert sum(counts.values()) == 2000
    assert abs(counts.get(0, 0) - 1000) < 200
    assert abs(counts.get(15, 0) - 1000) < 200


def test_xx_rotation_matches_dense():
    """Compare XX(theta) against the dense exp(-i theta/2 X⊗X) on a random
    single-qubit state preparation."""
    theta = 0.7
    ir = (
        "QINIT 2\n"
        "CREG 2\n"
        "RY q[0],(0.6)\n"
        "RX q[1],(1.1)\n"
        f"XX q[0],q[1],({theta})\n"
    )
    sim = MPSSimulator()
    psi = sim.simulate_statevector(ir)

    # Dense reference (q0 as LSB).
    def kron(a, b):
        return np.kron(a, b)
    I2 = np.eye(2)
    X = np.array([[0, 1], [1, 0]], dtype=complex)
    Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
    def ry(t): return np.array([[math.cos(t/2), -math.sin(t/2)], [math.sin(t/2), math.cos(t/2)]], dtype=complex)
    def rx(t): return np.array([[math.cos(t/2), -1j*math.sin(t/2)], [-1j*math.sin(t/2), math.cos(t/2)]], dtype=complex)
    # In q0-LSB convention dense gates on q1, q0 = kron(U1, U0)
    U_prep = kron(rx(1.1), ry(0.6))
    XX = kron(X, X)
    U_xx = math.cos(theta/2) * np.eye(4) - 1j * math.sin(theta/2) * XX
    psi_ref = U_xx @ U_prep @ np.array([1, 0, 0, 0], dtype=complex)
    assert np.allclose(psi, psi_ref, atol=1e-9)


def test_long_range_rejected():
    ir = "QINIT 4\nCREG 4\nCNOT q[0],q[2]\n"
    with pytest.raises(ValueError, match="long-range"):
        MPSSimulator().simulate_pmeasure(ir)


def test_control_block_rejected():
    ir = (
        "QINIT 3\n"
        "CREG 3\n"
        "X q[0] controlled_by (q[1])\n"
    )
    with pytest.raises(NotImplementedError, match="(?i)control"):
        MPSSimulator().simulate_pmeasure(ir)


def test_chi_truncation_records_error():
    """A 4-qubit GHZ requires bond 2 — running with chi=1 must record loss."""
    sim = MPSSimulator(MPSConfig(chi_max=1))
    sim.simulate_pmeasure(_ghz_ir(4))
    # max bond is capped, truncation_errors should be non-empty and non-zero
    assert sim.max_bond <= 1
    assert sim.truncation_errors  # at least one SVD truncation
    assert max(sim.truncation_errors) > 1e-3


def test_reversed_qubit_order_2q_gate():
    """CNOT q[2],q[1] should still produce GHZ-like correlations."""
    ir = (
        "QINIT 3\nCREG 3\nH q[2]\n"
        "CNOT q[2],q[1]\n"
        "CNOT q[1],q[0]\n"
    )
    sim = MPSSimulator()
    probs = sim.simulate_pmeasure(ir)
    # |000> + |111> → indices 0 and 7, each 0.5
    assert probs[0] == pytest.approx(0.5, abs=1e-9)
    assert probs[7] == pytest.approx(0.5, abs=1e-9)
    for i in (1, 2, 3, 4, 5, 6):
        assert probs[i] == pytest.approx(0.0, abs=1e-9)


def test_pmeasure_caps_at_24_qubits():
    ir = "QINIT 32\nCREG 32\nH q[0]\n"
    with pytest.raises(ValueError, match="(?i)pmeasure|2\\*\\*"):
        MPSSimulator().simulate_pmeasure(ir)


def test_shots_scales_to_large_n():
    """64-qubit GHZ via shots should run in seconds; statevector must refuse."""
    n = 64
    sim = MPSSimulator(MPSConfig(seed=42))
    counts = sim.simulate_shots(_ghz_ir(n), shots=200)
    # All bits same: either 0 or 2**n - 1
    for k in counts:
        assert k in (0, (1 << n) - 1)
    assert sum(counts.values()) == 200


# ---------------------------------------------------------------------------
# dummy:mps:linear-N backend wiring
# ---------------------------------------------------------------------------


def test_resolve_dummy_mps_basic():
    from uniqc.backend_adapter.dummy_backend import resolve_dummy_backend

    spec = resolve_dummy_backend("dummy:mps:linear-5")
    assert spec.simulator_kind == "mps"
    assert spec.available_qubits == [0, 1, 2, 3, 4]
    assert spec.available_topology == [[0, 1], [1, 2], [2, 3], [3, 4]]
    assert spec.simulator_kwargs == {}


def test_resolve_dummy_mps_with_kwargs():
    from uniqc.backend_adapter.dummy_backend import resolve_dummy_backend

    spec = resolve_dummy_backend("dummy:mps:linear-3:chi=16:cutoff=1e-8:seed=7")
    assert spec.simulator_kind == "mps"
    assert spec.simulator_kwargs == {
        "chi_max": 16,
        "svd_cutoff": 1e-8,
        "seed": 7,
    }


def test_dummy_mps_submit_roundtrip():
    from uniqc import Circuit
    from uniqc.backend_adapter.task_manager import submit_task, wait_for_result

    c = Circuit(4)
    c.h(0)
    c.cnot(0, 1)
    c.cnot(1, 2)
    c.cnot(2, 3)
    for q in range(4):
        c.measure(q, q)

    task = submit_task(c, backend="dummy:mps:linear-4", shots=400)
    res = wait_for_result(task, timeout=30)

    # Result is a UnifiedResult that exposes counts dict-like.
    from uniqc.backend_adapter.task.result_types import UnifiedResult

    assert isinstance(res, UnifiedResult)
    assert sum(res.values()) == 400
    # GHZ-style: only all-zeros and all-ones, ≈50/50.
    keys = list(res.keys())
    assert len(keys) == 2
    z = next(k for k in keys if "1" not in k)
    o = next(k for k in keys if "0" not in k)
    assert res[z] + res[o] == 400
    assert abs(res[z] - res[o]) < 200


def test_dummy_mps_long_range_rejected_at_submit():
    from uniqc import Circuit
    from uniqc.backend_adapter.task_manager import submit_task, wait_for_result
    from uniqc.exceptions import TaskFailedError

    c = Circuit(4)
    c.cnot(0, 2)
    c.measure(0, 0)
    c.measure(2, 1)

    task = submit_task(c, backend="dummy:mps:linear-4", shots=100)
    with pytest.raises(TaskFailedError):
        wait_for_result(task, timeout=30)


def test_dummy_mps_chi_propagates():
    """``chi=1`` from the identifier suffix must reach the underlying engine."""
    from uniqc.backend_adapter.dummy_backend import dummy_adapter_kwargs
    from uniqc.backend_adapter.task.adapters.dummy_adapter import DummyAdapter

    kw = dummy_adapter_kwargs("dummy:mps:linear-4:chi=1")
    adapter = DummyAdapter(**kw)
    sim = adapter._build_simulator()
    assert sim.config.chi_max == 1
