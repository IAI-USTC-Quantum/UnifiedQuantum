"""Tests for the RegionSelector class."""

from __future__ import annotations

from uniqc.backend_info import Platform
from uniqc.cli.chip_info import (
    ChipCharacterization,
    ChipGlobalInfo,
    QubitTopology,
    SingleQubitData,
    TwoQubitData,
    TwoQubitGateData,
)
from uniqc.region_selector import RegionSelector

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_chip(
    nodes: list[int], edges: list[tuple[int, int]], sq_fid: float = 0.99, tq_fid: float = 0.95
) -> ChipCharacterization:
    """Build a minimal ChipCharacterization for testing."""
    sq_data = tuple(
        SingleQubitData(
            qubit_id=q,
            t1=50.0,
            t2=50.0,
            single_gate_fidelity=sq_fid,
            readout_fidelity_0=0.99,
            readout_fidelity_1=0.99,
            avg_readout_fidelity=0.99,
        )
        for q in sorted(nodes)
    )
    tq_data = tuple(
        TwoQubitData(
            qubit_u=u,
            qubit_v=v,
            gates=(TwoQubitGateData(gate="cz", fidelity=tq_fid),),
        )
        for u, v in edges
    )
    return ChipCharacterization(
        platform=Platform.ORIGINQ,
        chip_name="test",
        full_id="test",
        available_qubits=tuple(sorted(nodes)),
        connectivity=tuple(QubitTopology(u=u, v=v) for u, v in edges),
        single_qubit_data=sq_data,
        two_qubit_data=tq_data,
        global_info=ChipGlobalInfo(),
        calibrated_at=None,
    )


# ---------------------------------------------------------------------------
# find_best_1D_chain tests
# ---------------------------------------------------------------------------


class TestFindBest1DChain:
    """Tests for find_best_1D_chain."""

    def test_chain_exact_length_from_start(self):
        """Greedy from start=0 on a 6-qubit chain returns [0,1,2,3] for length=4."""
        chip = _make_chip(list(range(6)), [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)])
        rs = RegionSelector(chip)
        result = rs.find_best_1D_chain(4, start=0)
        assert result.chain == [0, 1, 2, 3]
        assert result.estimated_fidelity is not None
        assert result.num_swaps == 0

    def test_chain_exact_length_from_middle_start(self):
        """Greedy from start=2 on a 6-qubit chain returns [2,3,4,5] for length=4."""
        chip = _make_chip(list(range(6)), [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)])
        rs = RegionSelector(chip)
        result = rs.find_best_1D_chain(4, start=2)
        assert result.chain == [2, 3, 4, 5]

    def test_chain_no_start_returns_lexicographically_first(self):
        """Without start, returns the lexicographically first chain of length 4."""
        chip = _make_chip(list(range(6)), [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)])
        rs = RegionSelector(chip)
        result = rs.find_best_1D_chain(4)
        assert result.chain == [0, 1, 2, 3]

    def test_chain_full_length(self):
        """Length=6 on a 6-qubit chain returns the full chain."""
        chip = _make_chip(list(range(6)), [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)])
        rs = RegionSelector(chip)
        result = rs.find_best_1D_chain(6)
        assert result.chain == [0, 1, 2, 3, 4, 5]

    def test_chain_partial_when_exact_unavailable(self):
        """When exact length is unavailable, returns the best partial chain."""
        chip = _make_chip(list(range(3)), [(0, 1), (1, 2)])
        rs = RegionSelector(chip)
        result = rs.find_best_1D_chain(4)
        assert result.chain == [0, 1, 2]
        assert len(result.chain) < 4
        assert result.estimated_fidelity is not None

    def test_chain_length_one(self):
        """Length=1 returns [start] or the first qubit."""
        chip = _make_chip(list(range(3)), [(0, 1), (1, 2)])
        rs = RegionSelector(chip)
        result = rs.find_best_1D_chain(1)
        assert result.chain is not None
        assert len(result.chain) == 1

    def test_chain_unknown_start_returns_none(self):
        """Unknown start qubit returns None."""
        chip = _make_chip(list(range(3)), [(0, 1), (1, 2)])
        rs = RegionSelector(chip)
        result = rs.find_best_1D_chain(2, start=99)
        assert result.chain is None

    def test_fidelity_in_range(self):
        """Fidelity estimate is between 0 and 1."""
        chip = _make_chip(list(range(6)), [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)])
        rs = RegionSelector(chip)
        result = rs.find_best_1D_chain(4)
        assert 0.0 <= result.estimated_fidelity <= 1.0


class TestEstimateCircuitFidelity:
    """Tests for estimate_circuit_fidelity."""

    def test_single_qubit_gates(self):
        """Single-qubit fidelity = 0.99 each → total ≈ 0.99^3."""
        from uniqc.circuit_builder import Circuit

        chip = _make_chip([0, 1], [(0, 1)])
        rs = RegionSelector(chip)
        circuit = Circuit(1)
        circuit.h(0)
        circuit.x(0)
        circuit.y(0)
        fid = rs.estimate_circuit_fidelity(circuit, qubits={0})
        assert 0.9 < fid < 1.0

    def test_missing_qubit_uses_default_fidelity(self):
        """Qubits not in characterization get default 0.99 fidelity."""
        from uniqc.circuit_builder import Circuit

        chip = _make_chip([0], [])
        rs = RegionSelector(chip)
        circuit = Circuit(2)
        circuit.h(0)
        circuit.h(1)
        fid = rs.estimate_circuit_fidelity(circuit, qubits={0, 1})
        assert fid > 0.95  # both at default 0.99

    def test_two_qubit_gate_included(self):
        """Two-qubit gate fidelity is multiplied in."""
        from uniqc.circuit_builder import Circuit

        chip = _make_chip([0, 1], [(0, 1)], tq_fid=0.95)
        rs = RegionSelector(chip)
        circuit = Circuit(2)
        circuit.h(0)
        circuit.cnot(0, 1)
        fid = rs.estimate_circuit_fidelity(circuit, qubits={0, 1})
        # 0.99 (1Q) * 0.95 (2Q) ≈ 0.9405
        assert 0.9 < fid < 1.0


class TestGetRankings:
    """Tests for ranking helper methods."""

    def test_qubit_rankings_sorted_descending(self):
        """Qubit rankings are sorted by fidelity descending."""
        chip = _make_chip([0, 1, 2], [(0, 1), (1, 2)], sq_fid=0.98)
        rs = RegionSelector(chip)
        rankings = rs.get_qubit_rankings()
        fids = [f for _, f in rankings]
        assert fids == sorted(fids, reverse=True)

    def test_edge_rankings_sorted_descending(self):
        """Edge rankings are sorted by fidelity descending."""
        chip = _make_chip([0, 1, 2], [(0, 1), (1, 2)], tq_fid=0.96)
        rs = RegionSelector(chip)
        rankings = rs.get_edge_rankings()
        fids = [f for _, f in rankings]
        assert fids == sorted(fids, reverse=True)
