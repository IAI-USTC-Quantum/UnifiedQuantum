"""Topology edge generation for HEA entangling layers."""

from __future__ import annotations

from typing import List, Tuple

from ._types import EntanglementTopology

__all__ = ["generate_edges"]

TopologyEdge = Tuple[int, int]


def generate_edges(
    qubits: List[int],
    topology: EntanglementTopology,
    custom_edges: List[TopologyEdge] | None = None,
    layer_index: int = 0,
) -> List[TopologyEdge]:
    """Generate directed entangling-gate edges for the given topology.

    Args:
        qubits: Qubit indices to use.
        topology: Named topology type.
        custom_edges: Required when topology is CUSTOM. List of (control, target) pairs.
        layer_index: Used for BRICKWORK to alternate even/odd pairing across layers.

    Returns:
        List of (control_qubit, target_qubit) edges.

    Raises:
        ValueError: CUSTOM topology with invalid or empty edges.
    """
    n = len(qubits)
    if n < 2:
        return []

    if topology == EntanglementTopology.LINEAR:
        return [(qubits[i], qubits[i + 1]) for i in range(n - 1)]

    if topology == EntanglementTopology.RING:
        edges = [(qubits[i], qubits[i + 1]) for i in range(n - 1)]
        edges.append((qubits[-1], qubits[0]))
        return edges

    if topology == EntanglementTopology.FULL:
        edges = []
        for i in range(n):
            for j in range(i + 1, n):
                edges.append((qubits[i], qubits[j]))
        return edges

    if topology == EntanglementTopology.STAR:
        return [(qubits[0], qubits[i]) for i in range(1, n)]

    if topology == EntanglementTopology.BRICKWORK:
        # Even layer: (0,1), (2,3), ...
        # Odd layer:  (1,2), (3,4), ...
        if layer_index % 2 == 0:
            return [(qubits[i], qubits[i + 1]) for i in range(0, n - 1, 2)]
        else:
            return [(qubits[i], qubits[i + 1]) for i in range(1, n - 1, 2)]

    if topology == EntanglementTopology.CUSTOM:
        if not custom_edges:
            raise ValueError("CUSTOM topology requires custom_edges to be provided")
        # Validate and map to actual qubit indices
        qubit_set = set(qubits)
        mapped = []
        for u, v in custom_edges:
            if u not in qubit_set or v not in qubit_set:
                raise ValueError(
                    f"Custom edge ({u}, {v}) contains qubits not in the qubit set {qubits}"
                )
            mapped.append((u, v))
        return mapped

    raise ValueError(f"Unknown topology: {topology}")


def count_edges_per_layer(
    qubits: List[int],
    topology: EntanglementTopology,
    depth: int = 1,
    custom_edges: List[TopologyEdge] | None = None,
) -> List[int]:
    """Count number of edges per layer for parameter accounting.

    For brickwork topology, each layer may have a different edge count.
    For all other topologies, all layers have the same edge count.
    """
    if topology == EntanglementTopology.BRICKWORK:
        return [len(generate_edges(qubits, topology, custom_edges, i)) for i in range(depth)]
    else:
        n_edges = len(generate_edges(qubits, topology, custom_edges, 0))
        return [n_edges] * depth
