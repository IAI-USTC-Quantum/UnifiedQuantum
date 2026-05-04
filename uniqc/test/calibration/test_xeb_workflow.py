"""Tests for high-level XEB workflows."""

from __future__ import annotations


def test_1q_xeb_workflow_accepts_dummy_noise_model(tmp_path):
    """Dummy XEB workflows should run against a noisy adapter when requested."""
    from uniqc.algorithms.workflows import xeb_workflow

    results = xeb_workflow.run_1q_xeb_workflow(
        backend="dummy",
        qubits=[0],
        depths=[1, 2],
        n_circuits=2,
        shots=64,
        use_readout_em=False,
        noise_model={"depol": 0.2, "readout": 0.04},
        seed=0,
        cache_dir=str(tmp_path),
    )

    result = results[0]
    assert result.n_circuits == 2
    assert result.depths == (1, 2)
    assert result.fidelity_per_layer < 1.0
