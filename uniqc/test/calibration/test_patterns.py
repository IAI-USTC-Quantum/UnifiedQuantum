"""Tests for parallel pattern generator (DSatur graph coloring)."""

import pytest

from uniqc.calibration.xeb.patterns import (
    ParallelPatternGenerator,
    ParallelPatternResult,
)


class TestAutoMode:
    def test_chain_topology_two_rounds(self):
        """A chain 0-1-2-3 has chromatic number 2 (alternating edges can be parallel)."""
        topology = [(0, 1), (1, 2), (2, 3), (3, 4)]
        gen = ParallelPatternGenerator(topology)
        result = gen.auto_generate()
        # Should be colorable in 2 rounds
        assert result.n_rounds == 2
        assert result.chromatic_number == 2
        assert result.source == "auto"
        # All edges should appear exactly once
        all_edges = {tuple(sorted(g)) for group in result.groups for g in group}
        expected = {tuple(sorted(e)) for e in topology}
        assert all_edges == expected

    def test_single_edge(self):
        """A single edge needs only 1 round."""
        topology = [(0, 1)]
        gen = ParallelPatternGenerator(topology)
        result = gen.auto_generate()
        assert result.n_rounds == 1
        assert len(result.groups) == 1

    def test_disjoint_edges(self):
        """Two non-overlapping edges (e.g. 0-1 and 2-3) can be in the same round."""
        topology = [(0, 1), (2, 3)]
        gen = ParallelPatternGenerator(topology)
        result = gen.auto_generate()
        # Should be 1 round (disjoint)
        assert result.n_rounds == 1
        assert len(result.groups) == 1
        assert set(result.groups[0]) == {(0, 1), (2, 3)}

    def test_star_topology(self):
        """Star: 0-1, 0-2, 0-3 needs 3 rounds (conflict graph is K3: chromatic number 3)."""
        topology = [(0, 1), (0, 2), (0, 3)]
        gen = ParallelPatternGenerator(topology)
        result = gen.auto_generate()
        # The conflict graph is K3 (each pair of edges shares qubit 0), chromatic number = 3
        assert result.n_rounds == 3
        assert result.chromatic_number == 3
        # All edges covered
        all_edges = {tuple(sorted(g)) for group in result.groups for g in group}
        expected = {tuple(sorted(e)) for e in topology}
        assert all_edges == expected

    def test_empty_topology(self):
        """Empty topology gives 0 rounds."""
        gen = ParallelPatternGenerator([])
        result = gen.auto_generate()
        assert result.n_rounds == 0
        assert result.groups == ()

    def test_chromatic_number_lower_bound(self):
        """Chromatic number >= max edge color degree (degree of conflict graph)."""
        # Path 0-1-2-3-4: conflict graph is a path of 4 edges
        # Max degree = 2, but chromatic number = 2 for a path
        topology = [(0, 1), (1, 2), (2, 3), (3, 4)]
        gen = ParallelPatternGenerator(topology)
        result = gen.auto_generate()
        assert result.chromatic_number <= result.n_rounds
        assert result.chromatic_number >= 2


class TestCircuitMode:
    def test_simple_circuit_no_2q_gates(self):
        """Circuit with no 2-qubit gates gives 0 rounds."""
        originir = "QINIT 1\nH q[0]\nMEASURE q[0], c[0]"
        gen = ParallelPatternGenerator(topology=[])
        result = gen.from_circuit(originir)
        assert result.n_rounds == 0
        assert result.source == "circuit"

    def test_circuit_single_2q_gate(self):
        """Single CNOT → 1 round."""
        originir = "QINIT 2\nCNOT q[0], q[1]\nMEASURE q[0], c[0]\nMEASURE q[1], c[1]"
        gen = ParallelPatternGenerator(topology=[])
        result = gen.from_circuit(originir)
        assert result.n_rounds == 1
        assert result.groups[0] == ((0, 1),)

    def test_circuit_sequential_gates(self):
        """Two CNOTs sharing a qubit → 2 rounds."""
        originir = (
            "QINIT 3\n"
            "CNOT q[0], q[1]\n"
            "CNOT q[1], q[2]\n"
            "MEASURE q[0], c[0]\n"
            "MEASURE q[1], c[1]\n"
            "MEASURE q[2], c[2]"
        )
        gen = ParallelPatternGenerator(topology=[])
        result = gen.from_circuit(originir)
        assert result.n_rounds == 2

    def test_circuit_parallel_gates(self):
        """Two non-overlapping CNOTs → 1 round."""
        originir = (
            "QINIT 4\n"
            "CNOT q[0], q[1]\n"
            "CNOT q[2], q[3]\n"
            "MEASURE q[0], c[0]\n"
            "MEASURE q[1], c[1]\n"
            "MEASURE q[2], c[2]\n"
            "MEASURE q[3], c[3]"
        )
        gen = ParallelPatternGenerator(topology=[])
        result = gen.from_circuit(originir)
        assert result.n_rounds == 1

    def test_circuit_mixed(self):
        """Chain CNOT 0-1, CNOT 2-3, CNOT 1-2: conflict graph is a path (2-colorable)."""
        originir = (
            "QINIT 4\n"
            "CNOT q[0], q[1]\n"
            "CNOT q[2], q[3]\n"
            "CNOT q[1], q[2]\n"
            "MEASURE q[0], c[0]\n"
            "MEASURE q[1], c[1]\n"
            "MEASURE q[2], c[2]\n"
            "MEASURE q[3], c[3]"
        )
        gen = ParallelPatternGenerator(topology=[])
        result = gen.from_circuit(originir)
        # Conflict graph: (0,1)-(1,2)-(2,3) is a path, chromatic number = 2
        # (0,1) conflicts with (1,2); (2,3) conflicts with (1,2); (0,1) and (2,3) don't conflict
        assert result.n_rounds == 2
        assert result.chromatic_number == 2
