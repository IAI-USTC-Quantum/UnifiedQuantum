"""Tests for XEB circuit generators."""

import pytest

from uniqc.calibration.xeb.circuits import (
    generate_1q_xeb_circuits,
    generate_2q_xeb_circuit,
    generate_2q_xeb_circuits,
)


class TestGenerate1qXEB:
    def test_circuit_count(self):
        depths = [5, 10, 20]
        n = 3
        circuits = generate_1q_xeb_circuits(qubit=0, depths=depths, n_circuits=n)
        assert len(circuits) == len(depths) * n

    def test_circuit_depth(self):
        depths = [5, 10]
        circuits = generate_1q_xeb_circuits(qubit=0, depths=depths, n_circuits=1)
        # Each depth should produce exactly 1 circuit
        assert len(circuits) == len(depths)
        for i, d in enumerate(depths):
            c = circuits[i]
            # Count gate lines (non-header, non-measure)
            lines = [l for l in c.originir.splitlines()
                     if l.strip() and not l.startswith("QINIT") and not l.startswith("CREG")
                     and not l.startswith("MEASURE")]
            assert len(lines) == d, f"Expected {d} gates, got {len(lines)}"

    def test_measure_present(self):
        circuits = generate_1q_xeb_circuits(qubit=0, depths=[5], n_circuits=1)
        assert "MEASURE" in circuits[0].originir

    def test_reproducibility(self):
        c1 = generate_1q_xeb_circuits(qubit=0, depths=[10], n_circuits=1, seed=42)
        c2 = generate_1q_xeb_circuits(qubit=0, depths=[10], n_circuits=1, seed=42)
        assert c1[0].originir == c2[0].originir

    def test_different_seed_different_circuit(self):
        c1 = generate_1q_xeb_circuits(qubit=0, depths=[10], n_circuits=1, seed=1)
        c2 = generate_1q_xeb_circuits(qubit=0, depths=[10], n_circuits=1, seed=2)
        assert c1[0].originir != c2[0].originir


class TestGenerate2qXEB:
    def test_circuit_structure(self):
        c = generate_2q_xeb_circuit(qubit_u=0, qubit_v=1, depth=3, seed=42)
        originir = c.originir
        assert "QINIT 2" in originir
        assert "MEASURE" in originir

    def test_depth_correct(self):
        for depth in [1, 5, 10]:
            c = generate_2q_xeb_circuit(qubit_u=3, qubit_v=7, depth=depth, seed=42)
            lines = [l for l in c.originir.splitlines()
                     if l.strip() and not l.startswith("QINIT") and not l.startswith("CREG")
                     and not l.startswith("MEASURE")]
            # Each layer: 2 random 1q gates + 1 2q gate = 3 gates
            assert len(lines) == 3 * depth, f"Expected {3*depth} gates, got {len(lines)}"

    def test_list_output(self):
        circuits = generate_2q_xeb_circuits(qubit_u=0, qubit_v=1, depths=[5, 10], n_circuits=2, seed=42)
        assert len(circuits) == 4  # 2 depths × 2 circuits

    def test_entangler_gate(self):
        c = generate_2q_xeb_circuit(qubit_u=0, qubit_v=1, depth=2, entangler_gate="CZ", seed=42)
        assert "CZ" in c.originir
