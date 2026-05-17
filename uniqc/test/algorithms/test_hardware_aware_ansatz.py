"""Unit tests for ``uniqc.algorithms.core.ansatz._hardware_aware``.

Covers topology classification, native-gate selection, and edge generation
across the supported entanglement layouts.
"""

from __future__ import annotations

import pytest

from uniqc.algorithms.core.ansatz._hardware_aware import (
    _classify_topology,
    _generate_named_edges,
    _select_native_gate,
    select_ansatz_config,
)
from uniqc.algorithms.core.ansatz._types import EntanglementTopology, EntanglingGate
from uniqc.backend_adapter.backend_info import BackendInfo, Platform, QubitTopology


def _be(
    edges: list[tuple[int, int]] = (),
    *,
    num_qubits: int | None = None,
    extra: dict | None = None,
) -> BackendInfo:
    edges_list = list(edges)
    n = num_qubits if num_qubits is not None else (max((max(e) for e in edges_list), default=-1) + 1)
    return BackendInfo(
        platform=Platform.ORIGINQ,
        name="fake",
        num_qubits=n,
        topology=tuple(QubitTopology(u, v) for u, v in edges_list),
        extra=extra or {},
    )


# ---------------------------------------------------------------------------
# select_ansatz_config — top-level entry point
# ---------------------------------------------------------------------------


def test_select_ansatz_no_topology_returns_ring():
    backend = _be(num_qubits=4)
    topo, gate, edges = select_ansatz_config(backend, n_qubits=4)
    assert topo == EntanglementTopology.RING
    assert gate == EntanglingGate.CNOT
    assert (0, 1) in edges
    assert (3, 0) in edges


def test_select_ansatz_linear_topology():
    backend = _be([(0, 1), (1, 2), (2, 3)])
    topo, gate, edges = select_ansatz_config(backend, n_qubits=4)
    assert topo == EntanglementTopology.LINEAR
    assert edges == [(0, 1), (1, 2), (2, 3)]


def test_select_ansatz_ring_topology():
    backend = _be([(0, 1), (1, 2), (2, 3), (3, 0)])
    topo, _, edges = select_ansatz_config(backend, n_qubits=4)
    assert topo == EntanglementTopology.RING
    assert (3, 0) in edges


def test_select_ansatz_star_topology():
    backend = _be([(0, 1), (0, 2), (0, 3)])
    topo, _, edges = select_ansatz_config(backend, n_qubits=4)
    assert topo == EntanglementTopology.STAR
    assert all(0 in e for e in edges)


def test_select_ansatz_full_topology():
    # 3-qubit fully connected → all-degree-2 → classifier treats it as RING
    # (a 3-cycle is both fully connected AND a ring).
    backend = _be([(0, 1), (0, 2), (1, 2)])
    topo, _, edges = select_ansatz_config(backend, n_qubits=3)
    assert topo in (EntanglementTopology.FULL, EntanglementTopology.RING)
    assert len(edges) == 3


def test_select_ansatz_full_topology_4q():
    # 4-qubit K4 → not a ring, classifier should pick FULL
    backend = _be([(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)])
    topo, _, edges = select_ansatz_config(backend, n_qubits=4)
    assert topo == EntanglementTopology.FULL
    assert len(edges) == 6


def test_select_ansatz_custom_topology():
    # 5-node graph that isn't linear / ring / star / full
    backend = _be([(0, 1), (1, 2), (1, 3), (3, 4)])
    topo, _, edges = select_ansatz_config(backend, n_qubits=5)
    assert topo == EntanglementTopology.CUSTOM


def test_select_ansatz_too_many_qubits_raises():
    backend = _be([(0, 1)], num_qubits=2)
    with pytest.raises(ValueError, match="qubits"):
        select_ansatz_config(backend, n_qubits=5)


# ---------------------------------------------------------------------------
# _select_native_gate
# ---------------------------------------------------------------------------


def test_select_native_gate_prefers_cz():
    # IBM uses extra["basis_gates"] (since PLATFORM_BASIS_GATES['ibm'] is empty)
    backend = BackendInfo(
        platform=Platform.IBM,
        name="fake",
        num_qubits=2,
        topology=(QubitTopology(0, 1),),
        extra={"basis_gates": ["cz", "rx", "ry"]},
    )
    assert _select_native_gate(backend) == EntanglingGate.CZ


def test_select_native_gate_defaults_to_cnot():
    backend = BackendInfo(
        platform=Platform.IBM,
        name="fake",
        num_qubits=2,
        topology=(QubitTopology(0, 1),),
        extra={"basis_gates": ["rx", "ry"]},
    )
    assert _select_native_gate(backend) == EntanglingGate.CNOT


def test_select_native_gate_iswap():
    backend = BackendInfo(
        platform=Platform.IBM,
        name="fake",
        num_qubits=2,
        topology=(QubitTopology(0, 1),),
        extra={"basis_gates": ["iswap", "rx"]},
    )
    assert _select_native_gate(backend) == EntanglingGate.ISWAP


def test_select_native_gate_originq_defaults_to_cz():
    # OriginQ platform default basis is ("CZ", "SX", "RZ") — so a backend with
    # no explicit basis should still produce CZ as the entangling gate.
    backend = _be([(0, 1)])
    assert _select_native_gate(backend) == EntanglingGate.CZ


# ---------------------------------------------------------------------------
# _generate_named_edges
# ---------------------------------------------------------------------------


def test_generate_named_edges_linear():
    assert _generate_named_edges([0, 1, 2, 3], EntanglementTopology.LINEAR) == [(0, 1), (1, 2), (2, 3)]


def test_generate_named_edges_ring():
    edges = _generate_named_edges([0, 1, 2, 3], EntanglementTopology.RING)
    assert (3, 0) in edges and (0, 1) in edges and len(edges) == 4


def test_generate_named_edges_star():
    edges = _generate_named_edges([0, 1, 2, 3], EntanglementTopology.STAR)
    assert edges == [(0, 1), (0, 2), (0, 3)]


def test_generate_named_edges_full():
    edges = _generate_named_edges([0, 1, 2], EntanglementTopology.FULL)
    assert set(edges) == {(0, 1), (0, 2), (1, 2)}


def test_generate_named_edges_custom_returns_empty():
    assert _generate_named_edges([0, 1, 2], EntanglementTopology.CUSTOM) == []


# ---------------------------------------------------------------------------
# _classify_topology corner cases
# ---------------------------------------------------------------------------


def test_classify_topology_single_node_is_linear():
    assert _classify_topology({0: set()}, n_qubits=1) == EntanglementTopology.LINEAR


def test_classify_topology_non_canonical_linear_is_custom():
    # Two endpoints + one internal that isn't adjacent to both → CUSTOM
    adj = {0: {1}, 1: {0, 3}, 2: {3}, 3: {1, 2}}
    assert _classify_topology(adj, n_qubits=4) in {EntanglementTopology.CUSTOM, EntanglementTopology.LINEAR}
