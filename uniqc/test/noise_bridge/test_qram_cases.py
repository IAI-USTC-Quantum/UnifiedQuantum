"""Tests for the noisy-VM QRAM / QPU-addressing / mitigation cases."""

from __future__ import annotations

import pytest

from uniqc.noise_bridge import load_noise_model, write_synthetic_model
from uniqc.noise_bridge.qram_cases import (
    QRAM_CASE_DATA,
    build_qpu_addressing_circuit,
    build_qram_lookup_circuit,
    distribution_fidelity,
    ideal_data_distribution,
    run_qpu_addressing_case,
    run_qram_lookup_case,
)


@pytest.fixture(scope="module")
def model(tmp_path_factory):
    path = write_synthetic_model(tmp_path_factory.mktemp("nb") / "model.json", num_qubits=5, seed=42)
    return load_noise_model(path)


class TestLookupCase:
    def test_ideal_lookup_matches_qram_data(self, model):
        """The case circuit itself must reproduce QRAM semantics noiselessly."""
        from uniqc.simulator import Simulator

        for address in (0, 3, 5, 7):
            circuit = build_qram_lookup_circuit(address)
            sim = Simulator(backend_type="statevector")
            sim.simulate_preprocess(circuit)
            qram = sim.qram_objects["qram_case"]
            for a, v in enumerate(QRAM_CASE_DATA):
                qram.write(a, v)
            probs = list(sim.simulate_pmeasure(circuit))
            assert probs.index(max(probs)) == QRAM_CASE_DATA[address]

    @pytest.mark.requires_cpp
    def test_lookup_case_report(self, model, tmp_path):
        report = run_qram_lookup_case(model, address=5, shots=300, seed=3, workdir=tmp_path / "cal")
        assert report["case"] == "qram_lookup_3layer"
        assert report["expected_value"] == QRAM_CASE_DATA[5]
        assert report["mitigated_top_outcome"] == format(QRAM_CASE_DATA[5], "02b")
        assert report["raw_accuracy"] > 0.5
        assert sum(report["noisy_counts"].values()) == 300
        assert report["raw_fidelity"] > 0.6


class TestQPUAddressingCase:
    def test_ideal_distribution_spans_data_values(self, model):
        ideal = ideal_data_distribution(build_qpu_addressing_circuit())
        assert set(ideal) <= set(range(4))
        assert sum(ideal.values()) == pytest.approx(1.0)
        assert len(ideal) >= 3  # entangled addressing touches several values

    @pytest.mark.requires_cpp
    def test_qpu_case_report(self, model, tmp_path):
        report = run_qpu_addressing_case(model, shots=300, seed=4, workdir=tmp_path / "cal")
        assert report["case"] == "qpu_addressing_3layer_qram"
        assert report["raw_fidelity"] > 0.6
        assert report["mitigated_fidelity"] > 0.6
        assert sum(report["noisy_counts"].values()) == 300


class TestDistributionFidelity:
    def test_perfect_overlap(self):
        counts = {"10": 100}
        assert distribution_fidelity(counts, {2: 1.0}) == pytest.approx(1.0)

    def test_disjoint_support(self):
        assert distribution_fidelity({"01": 100}, {2: 1.0}) == 0.0

    def test_empty_counts(self):
        assert distribution_fidelity({}, {2: 1.0}) == 0.0
