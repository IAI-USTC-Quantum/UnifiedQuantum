"""Tests for the Quantum Volume benchmark entry."""

from __future__ import annotations

import numpy as np
import pytest

from uniqc.benchmark.quantum_volume import (
    build_qv_model_circuit,
    haar_su4,
    heavy_outputs_from_probabilities,
    run_quantum_volume,
)


def test_haar_su4_is_unitary_and_deterministic():
    rng = np.random.default_rng(5)
    u = haar_su4(rng)
    np.testing.assert_allclose(u.conj().T @ u, np.eye(4), atol=1e-12)
    rng2 = np.random.default_rng(5)
    np.testing.assert_allclose(u, haar_su4(rng2), atol=0)


def test_heavy_outputs_uniform_distribution_is_empty():
    # Strictly-greater-than-median semantics: an exactly uniform distribution
    # has no heavy outputs (degenerate but consistent; never occurs for
    # Haar-random model circuits).
    heavy = heavy_outputs_from_probabilities(np.full(4, 0.25))
    assert len(heavy) == 0


def test_heavy_outputs_perturbed_distribution():
    probs = np.array([0.26, 0.25, 0.25, 0.24])
    heavy = heavy_outputs_from_probabilities(probs)
    median = float(np.median(probs))  # 0.25
    assert heavy == frozenset(i for i, p in enumerate(probs) if p > median)
    assert 0 in heavy and 1 not in heavy


def test_heavy_outputs_skewed_distribution():
    probs = np.array([0.5, 0.3, 0.15, 0.05])
    heavy = heavy_outputs_from_probabilities(probs)
    median = float(np.median(probs))  # (0.15+0.3)/2 = 0.225
    assert heavy == frozenset(i for i, p in enumerate(probs) if p > median)


def test_heavy_outputs_rejects_unnormalized():
    with pytest.raises(ValueError, match="normalized"):
        heavy_outputs_from_probabilities(np.array([0.5, 0.6]))
    with pytest.raises(ValueError, match="at least two"):
        heavy_outputs_from_probabilities(np.array([1.0]))


def test_model_circuit_is_seed_deterministic():
    a = build_qv_model_circuit(3, seed=11).originir
    b = build_qv_model_circuit(3, seed=11).originir
    c = build_qv_model_circuit(3, seed=12).originir
    assert a == b
    assert a != c


def test_model_circuit_su4_block_preserves_unitary():
    """The decomposed block must reproduce the Haar SU(4) action (q0 = LSB)."""
    from uniqc.benchmark.quantum_volume import _apply_su4_ops
    from uniqc.circuit_builder.qcircuit import Circuit
    from uniqc.simulator import Simulator

    rng = np.random.default_rng(9)
    unitary = haar_su4(rng)
    circuit = Circuit()
    _apply_su4_ops(circuit, 0, 1, unitary)
    circuit.measure(0, 1)
    state = np.asarray(Simulator(backend_type="statevector").simulate_statevector(circuit.originir))
    # Reference: apply the SU(4) to |00>; index = 2*q1 + q0 (little-endian).
    reference = unitary @ np.array([1, 0, 0, 0], dtype=complex)
    np.testing.assert_allclose(np.abs(state) ** 2, np.abs(reference) ** 2, atol=1e-8)
    fidelity = abs(np.vdot(reference, state))
    assert fidelity > 0.999999


@pytest.mark.requires_cpp
def test_run_quantum_volume_ideal_backend_passes():
    result = run_quantum_volume(width=4, trials=3, shots=200, base_seed=1)
    assert result.passed
    assert result.quantum_volume == 16
    assert result.trials_passed == 3
    assert result.mean_h > 2.0 / 3.0
    payload = result.to_json_dict()
    assert payload["benchmark"] == "quantum_volume"
    assert len(payload["trial_results"]) == 3


def test_run_quantum_volume_rejects_nonlocal_backend():
    with pytest.raises(ValueError, match="dummy:local:simulator"):
        run_quantum_volume(width=2, trials=1, shots=10, backend="originq:WK_C180")


def test_run_quantum_volume_input_validation():
    with pytest.raises(ValueError, match="width"):
        run_quantum_volume(width=0, trials=1, shots=10)
    with pytest.raises(ValueError, match="trials"):
        run_quantum_volume(width=2, trials=0, shots=10)
    with pytest.raises(ValueError, match="shots"):
        run_quantum_volume(width=2, trials=1, shots=0)
