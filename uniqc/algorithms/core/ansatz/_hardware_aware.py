"""Hardware-aware ansatz configuration selection."""

from __future__ import annotations

from typing import List, Tuple

from uniqc.backend_adapter.backend_info import BackendInfo, QubitTopology
from uniqc.compile.policy import resolve_basis_gates

from ._types import EntanglingGate, EntanglementTopology

__all__ = ["select_ansatz_config"]

TopologyEdge = Tuple[int, int]


def select_ansatz_config(
    backend_info: BackendInfo,
    n_qubits: int,
) -> Tuple[EntanglementTopology, EntanglingGate, List[TopologyEdge]]:
    """Select topology and entangling gate based on hardware connectivity and basis gates.

    Args:
        backend_info: Backend information containing topology and capabilities.
        n_qubits: Number of qubits needed for the ansatz.

    Returns:
        Tuple of (topology, entangling_gate, edges) where:
        - topology: The selected entanglement topology
        - entangling_gate: The native or best-available entangling gate
        - edges: Coupling map edges for the requested n_qubits (for CUSTOM topology)

    Raises:
        ValueError: If backend has no topology or fewer qubits than requested.
    """
    # Build undirected adjacency from topology
    adjacency: dict[int, set[int]] = {}
    raw_edges: List[TopologyEdge] = []

    for edge in backend_info.topology:
        u, v = edge.u, edge.v
        raw_edges.append((u, v))
        if u not in adjacency:
            adjacency[u] = set()
        if v not in adjacency:
            adjacency[v] = set()
        adjacency[u].add(v)
        adjacency[v].add(u)

    if not raw_edges:
        # No topology info available, fall back to ring
        edges = [(i, (i + 1) % n_qubits) for i in range(n_qubits)]
        return EntanglementTopology.RING, EntanglingGate.CNOT, edges

    if backend_info.num_qubits < n_qubits:
        raise ValueError(
            f"Backend {backend_info.name} has {backend_info.num_qubits} qubits, "
            f"but {n_qubits} were requested"
        )

    # Classify the graph structure
    topology_type = _classify_topology(adjacency, n_qubits)

    # Select native entangling gate
    entangling_gate = _select_native_gate(backend_info)

    # For non-CUSTOM topologies, generate edges based on the type
    # For CUSTOM, return the restricted edge list
    if topology_type == EntanglementTopology.CUSTOM:
        # Restrict to first n_qubits
        available_qubits = sorted(adjacency.keys())[:n_qubits]
        qubit_set = set(available_qubits)
        edges = [(u, v) for u, v in raw_edges if u in qubit_set and v in qubit_set]
        return topology_type, entangling_gate, edges

    # Generate edges for named topologies
    edges = _generate_named_edges(available_qubits, topology_type)
    return topology_type, entangling_gate, edges


def _classify_topology(
    adjacency: dict[int, set[int]],
    n_qubits: int,
) -> EntanglementTopology:
    """Classify the coupling graph structure."""
    nodes = sorted(adjacency.keys())
    n = len(nodes)

    if n < 2:
        return EntanglementTopology.LINEAR

    degrees = [len(adjacency.get(n, set())) for n in nodes]

    # Check for linear chain: exactly two endpoints of degree 1, rest degree 2
    endpoints = [i for i, d in enumerate(degrees) if d == 1]
    internal = [i for i, d in enumerate(degrees) if d == 2]

    if len(endpoints) == 2 and len(internal) == n - 2:
        # Verify it's actually a chain (each internal node connects to its neighbors)
        for i in internal:
            ni = nodes[i]
            neighbors = adjacency.get(ni, set())
            expected = set()
            if i > 0:
                expected.add(nodes[i - 1])
            if i < n - 1:
                expected.add(nodes[i + 1])
            if neighbors != expected:
                return EntanglementTopology.CUSTOM
        return EntanglementTopology.LINEAR

    # Check for ring: all nodes degree 2
    if all(d == 2 for d in degrees):
        # Verify it's a cycle (each node connects to its two neighbors in sorted order)
        for i, ni in enumerate(nodes):
            neighbors = adjacency.get(ni, set())
            expected = {nodes[(i - 1) % n], nodes[(i + 1) % n]}
            if neighbors != expected:
                return EntanglementTopology.CUSTOM
        return EntanglementTopology.RING

    # Check for star: one center node connected to all others, all others degree 1
    for center_idx, center_deg in enumerate(degrees):
        if center_deg == n - 1:
            others = [i for i, d in enumerate(degrees) if i != center_idx]
            if all(degrees[i] == 1 for i in others):
                return EntanglementTopology.STAR

    # Check for full/fully connected
    expected_full_degree = n - 1
    if all(d == expected_full_degree for d in degrees):
        return EntanglementTopology.FULL

    # Fall back to custom
    return EntanglementTopology.CUSTOM


def _select_native_gate(backend_info: BackendInfo) -> EntanglingGate:
    """Select the best available native entangling gate."""
    # Try to get basis gates from backend info
    basis_gates = resolve_basis_gates(backend_info)

    # Check for native gates in priority order
    gate_priority = ["cz", "ecr", "cx", "cnot", "iswap"]

    for gate in gate_priority:
        if gate in basis_gates:
            if gate in ("cz",):
                return EntanglingGate.CZ
            elif gate in ("ecr",):
                return EntanglingGate.CNOT  # ECR is similar to CNOT
            elif gate in ("cx", "cnot"):
                return EntanglingGate.CNOT
            elif gate in ("iswap",):
                return EntanglingGate.ISWAP

    # Default to CNOT
    return EntanglingGate.CNOT


def _generate_named_edges(
    qubits: List[int],
    topology: EntanglementTopology,
) -> List[TopologyEdge]:
    """Generate edges for named topologies."""
    n = len(qubits)
    if topology == EntanglementTopology.LINEAR:
        return [(qubits[i], qubits[i + 1]) for i in range(n - 1)]
    elif topology == EntanglementTopology.RING:
        edges = [(qubits[i], qubits[i + 1]) for i in range(n - 1)]
        edges.append((qubits[-1], qubits[0]))
        return edges
    elif topology == EntanglementTopology.STAR:
        return [(qubits[0], qubits[i]) for i in range(1, n)]
    elif topology == EntanglementTopology.FULL:
        edges = []
        for i in range(n):
            for j in range(i + 1, n):
                edges.append((qubits[i], qubits[j]))
        return edges
    else:
        # For CUSTOM, return empty and let caller handle
        return []
