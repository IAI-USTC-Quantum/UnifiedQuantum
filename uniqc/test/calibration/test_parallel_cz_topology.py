"""Tests for parallel-CZ XEB topology helpers."""

from __future__ import annotations

import pytest

from uniqc.calibration.xeb.topology import (
    ChipTopologyView,
    Region,
    parallel_patterns,
    pick_chain_region,
    pick_region,
    three_color_chip,
)


def _make_view(
    n_qubits: int,
    edges: list[tuple[int, int]],
    *,
    bad_qubits: set[int] | None = None,
    bad_edges: set[tuple[int, int]] | None = None,
) -> ChipTopologyView:
    """Build a synthetic ChipTopologyView without going through ChipCharacterization."""
    bad_qubits = bad_qubits or set()
    bad_edges = bad_edges or set()
    e_1q = {q: (1e-3 if q not in bad_qubits else 5e-2) for q in range(n_qubits)}
    e_ro = dict.fromkeys(range(n_qubits), 0.01)
    norm_edges = tuple(sorted({(min(a, b), max(a, b)) for a, b in edges}))
    e_2q = {e: (1e-2 if e not in bad_edges else 1e-1) for e in norm_edges}
    return ChipTopologyView(
        enabled_qubits=tuple(range(n_qubits)),
        coupling_map=norm_edges,
        e_1q=e_1q,
        e_2q=e_2q,
        e_ro=e_ro,
    )


def test_parallel_patterns_disjoint_and_cover_all_edges():
    edges = [(i, i + 1) for i in range(7)]  # path of length 8
    patterns = parallel_patterns(edges)
    assert len(patterns) >= 2
    seen: set[tuple[int, int]] = set()
    for pat in patterns:
        qs_in_pat: set[int] = set()
        for a, b in pat:
            assert a not in qs_in_pat and b not in qs_in_pat, f"pattern {pat} not disjoint"
            qs_in_pat.update((a, b))
            seen.add((min(a, b), max(a, b)))
    assert seen == {(min(a, b), max(a, b)) for a, b in edges}


def test_parallel_patterns_path_two_colors():
    edges = [(i, i + 1) for i in range(5)]
    patterns = parallel_patterns(edges)
    # A path graph is 2-edge-colourable.
    assert len(patterns) == 2


def test_three_color_chip_partitions_all_edges():
    # Bipartite-ish 4x4 grid edges (max degree 4 -> may need >3 colors, but
    # we use a small kagome-ish subgraph with max degree 3).
    edges = [
        (0, 1),
        (1, 2),
        (2, 3),
        (4, 5),
        (5, 6),
        (6, 7),
        (0, 4),
        (1, 5),
        (2, 6),
        (3, 7),
    ]
    view = _make_view(8, edges)
    colors = three_color_chip(view, max_K=4)
    seen: set[tuple[int, int]] = set()
    for col in colors:
        qs: set[int] = set()
        for a, b in col:
            assert a not in qs and b not in qs
            qs.update((a, b))
            seen.add((min(a, b), max(a, b)))
    assert seen == {(min(a, b), max(a, b)) for a, b in edges}


def test_pick_region_returns_connected_subgraph():
    edges = [(i, i + 1) for i in range(9)]
    view = _make_view(10, edges)
    region = pick_region(view, n=4, seed=0)
    assert isinstance(region, Region)
    assert len(region.qubits) == 4
    # Connected: induced edges have to span 3 edges in the induced subgraph
    # (any chain of 4 qubits has exactly 3 consecutive edges).
    qs = set(region.qubits)
    induced = [(a, b) for (a, b) in edges if a in qs and b in qs]
    assert len(induced) >= 3


def test_pick_region_prefers_high_fidelity_qubits():
    edges = [(i, i + 1) for i in range(9)]
    # Make qubits 0..3 noisy; 5..9 clean.
    view = _make_view(10, edges, bad_qubits={0, 1, 2, 3})
    region = pick_region(view, n=3, seed=0)
    # Best 3-qubit chain should avoid the noisy qubits.
    assert all(q >= 4 for q in region.qubits)


def test_pick_region_rejects_invalid_size():
    edges = [(0, 1), (1, 2)]
    view = _make_view(3, edges)
    with pytest.raises(ValueError, match="positive"):
        pick_region(view, n=0)
    with pytest.raises(ValueError, match="enabled"):
        pick_region(view, n=10)


def test_pick_chain_region_returns_chord_free_chain():
    edges = [(i, i + 1) for i in range(9)]
    view = _make_view(10, edges)
    chain = pick_chain_region(view, length=5)
    assert len(chain.qubits) == 5
    assert len(chain.edges) == 4
    # Each consecutive qubit pair shares an edge.
    for i in range(4):
        a, b = chain.qubits[i], chain.qubits[i + 1]
        assert (min(a, b), max(a, b)) in chain.edges


def test_pick_chain_region_forced_qubits_validated():
    edges = [(0, 1), (1, 2), (2, 3), (3, 4)]
    view = _make_view(5, edges)
    chain = pick_chain_region(view, length=3, forced_qubits=[1, 2, 3])
    assert chain.qubits == (1, 2, 3)
    # Non-adjacent forced qubits should raise.
    with pytest.raises(ValueError, match="not adjacent"):
        pick_chain_region(view, length=3, forced_qubits=[0, 2, 4])


def test_chip_topology_view_from_characterization():
    from uniqc.backend_adapter.backend_info import Platform
    from uniqc.cli.chip_info import (
        ChipCharacterization,
        QubitTopology,
        SingleQubitData,
        TwoQubitData,
        TwoQubitGateData,
    )

    chip = ChipCharacterization(
        platform=Platform.DUMMY,
        chip_name="toy",
        full_id="dummy:toy",
        available_qubits=(0, 1, 2, 3),
        connectivity=(
            QubitTopology(u=0, v=1),
            QubitTopology(u=1, v=2),
            QubitTopology(u=2, v=3),
        ),
        single_qubit_data=tuple(
            SingleQubitData(
                qubit_id=q,
                single_gate_fidelity=0.999,
                avg_readout_fidelity=0.97,
            )
            for q in range(4)
        ),
        two_qubit_data=(
            TwoQubitData(qubit_u=0, qubit_v=1, gates=(TwoQubitGateData(gate="cz", fidelity=0.99),)),
            TwoQubitData(qubit_u=1, qubit_v=2, gates=(TwoQubitGateData(gate="cz", fidelity=0.98),)),
            TwoQubitData(qubit_u=2, qubit_v=3, gates=(TwoQubitGateData(gate="cz", fidelity=0.97),)),
        ),
    )
    view = ChipTopologyView.from_chip_characterization(chip)
    assert view.enabled_qubits == (0, 1, 2, 3)
    assert view.coupling_map == ((0, 1), (1, 2), (2, 3))
    assert view.e_2q[(0, 1)] == pytest.approx(1 - 0.99)
    assert view.e_1q[0] == pytest.approx(1 - 0.999)
    assert view.e_ro[0] == pytest.approx(1 - 0.97)
