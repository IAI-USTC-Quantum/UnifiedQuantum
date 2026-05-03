"""Parallel pattern generation for 2-qubit XEB.

Provides two modes:
- **auto** mode: Given chip topology (list of edges), computes the minimum
  parallel schedule using DSatur graph coloring on the conflict graph.
- **circuit** mode: Given a compiled OriginIR circuit, extracts all 2-qubit
  gates and computes its effective parallelism schedule.

The conflict graph has one vertex per 2-qubit gate (or per edge in the
chip topology for auto mode). Two vertices conflict if they share a qubit,
meaning they cannot be executed in the same parallel round.
"""

from __future__ import annotations

import collections
import dataclasses
from typing import Any

__all__ = [
    "ParallelPatternResult",
    "ParallelPatternGenerator",
]


@dataclasses.dataclass(frozen=True, slots=True)
class ParallelPatternResult:
    """Result of a parallel pattern generation computation."""

    groups: tuple[tuple[tuple[int, int], ...], ...]
    n_rounds: int
    chromatic_number: int  # lower bound = max edge-color-degree
    source: str  # "auto" | "circuit"

    def to_dict(self) -> dict[str, Any]:
        return {
            "groups": [list(g) for g in self.groups],
            "n_rounds": self.n_rounds,
            "chromatic_number": self.chromatic_number,
            "source": self.source,
        }


# ---------------------------------------------------------------------------
# DSatur graph coloring
# ---------------------------------------------------------------------------


def _dsatur_color(
    conflict_adj: dict[int, set[int]],
) -> dict[int, int]:
    """Color a graph using the DSatur (saturation degree) greedy heuristic.

    Args:
        conflict_adj: Adjacency dict mapping vertex ID to set of neighbor IDs.

    Returns:
        Dict mapping vertex ID to color (integer, starting at 0).
    """
    vertices = list(conflict_adj.keys())
    if not vertices:
        return {}

    # color[v] = assigned color, or None if uncolored
    color: dict[int, int | None] = dict.fromkeys(vertices)
    # available_colors[v] = set of colors already used by neighbors of v
    neighbor_colors: dict[int, set[int]] = {v: set() for v in vertices}

    uncolored = set(vertices)

    while uncolored:
        # Pick the uncolored vertex with highest saturation degree
        # (number of differently-colored neighbors)
        def saturation(v: int) -> int:
            return len(neighbor_colors[v])

        max_sat = max(saturation(v) for v in uncolored)
        # Among those with max saturation, pick highest degree (number of neighbors)
        candidates = [v for v in uncolored if saturation(v) == max_sat]
        v = max(candidates, key=lambda x: len(conflict_adj[x]))

        # Assign the smallest color not used by neighbors
        used = neighbor_colors[v]
        c = 0
        while c in used:
            c += 1
        color[v] = c

        # Update neighbor_colors for uncolored neighbors
        for u in uncolored:
            if u != v and v in conflict_adj.get(u, ()):
                neighbor_colors[u].add(c)

        uncolored.remove(v)

    return color  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Auto mode: from chip topology
# ---------------------------------------------------------------------------


def _build_conflict_graph_from_topology(
    edges: list[tuple[int, int]],
) -> tuple[dict[tuple[int, int], set[tuple[int, int]]], dict[tuple[int, int], int]]:
    """Build conflict graph from chip topology.

    Vertices = edges in the chip topology.
    Two vertices (edges) conflict if they share a qubit.

    Returns:
        conflict_adj: adjacency dict of the conflict graph
        vertex_to_idx: mapping from (u,v) to integer index
    """
    vertex_to_idx: dict[tuple[int, int], int] = {}
    for i, (u, v) in enumerate(sorted(edges)):
        vertex_to_idx[(u, v)] = i

    n = len(edges)
    conflict_adj: dict[int, set[int]] = {i: set() for i in range(n)}

    edge_list = sorted(edges)
    for i, (u1, v1) in enumerate(edge_list):
        for j, (u2, v2) in enumerate(edge_list):
            if j <= i:
                continue
            # Conflict if edges share a qubit
            if {u1, v1} & {u2, v2}:
                conflict_adj[i].add(j)
                conflict_adj[j].add(i)

    return conflict_adj, vertex_to_idx


# ---------------------------------------------------------------------------
# Circuit mode: from OriginIR
# ---------------------------------------------------------------------------

# Supported 2-qubit gate names in OriginIR
_2Q_GATE_NAMES = frozenset({"CNOT", "CZ", "ECR", "SWAP", "ISWAP", "XX", "YY", "ZZ", "XY"})


def _parse_2q_gates_from_originir(originir: str) -> list[tuple[int, int]]:
    """Extract all 2-qubit gate pairs from an OriginIR string.

    Returns:
        List of (qubit_u, qubit_v) pairs in execution order.
    """
    pairs: list[tuple[int, int]] = []
    for line in originir.splitlines():
        line = line.strip()
        if not line:
            continue
        # Gate name is the first token
        parts = line.split()
        gate = parts[0]
        if gate not in _2Q_GATE_NAMES:
            continue
        # Reconstruct the full line after the gate name (handles "q[0], q[1]" with comma)
        # parts = ["CNOT", "q[0],", "q[1]"]
        if len(parts) < 3:
            continue
        content = " ".join(parts[1:])
        # Find all q[N] patterns
        import re

        qs = re.findall(r"q\[(\d+)\]", content)
        if len(qs) >= 2:
            u, v = int(qs[0]), int(qs[1])
            pairs.append((u, v))
    return pairs


def _build_conflict_graph_from_pairs(
    pairs: list[tuple[int, int]],
) -> tuple[dict[int, set[int]], list[tuple[int, int]]]:
    """Build conflict graph from a list of 2-qubit gate pairs.

    Vertices = gates (ordered pairs). Two gates conflict if they share a qubit.
    """
    n = len(pairs)
    conflict_adj: dict[int, set[int]] = {i: set() for i in range(n)}

    for i, (u1, v1) in enumerate(pairs):
        for j in range(i + 1, n):
            u2, v2 = pairs[j]
            if {u1, v1} & {u2, v2}:
                conflict_adj[i].add(j)
                conflict_adj[j].add(i)

    return conflict_adj, pairs


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class ParallelPatternGenerator:
    """Generator for parallel execution patterns of 2-qubit gates.

    Supports two modes:
    - ``auto``: Given a chip topology, partition all edges into parallel
      groups that can be executed simultaneously.
    - ``circuit``: Given an OriginIR string, extract all 2-qubit gates
      and compute the minimal parallel schedule for that circuit.
    """

    def __init__(self, topology: list[tuple[int, int]]) -> None:
        """Initialize with the chip qubit connectivity topology.

        Args:
            topology: List of (u, v) edges representing physical qubit
                connectivity. All edges in the topology will be included
                in the parallel schedule.
        """
        self.topology = topology

    def auto_generate(self) -> ParallelPatternResult:
        """Auto-generate parallel patterns for all edges in the topology.

        Uses DSatur graph coloring on the conflict graph to find a
        minimal parallel schedule.

        Returns:
            ParallelPatternResult with groups of edges that can be executed
            in parallel in each round.
        """
        conflict_adj, vertex_to_idx = _build_conflict_graph_from_topology(self.topology)
        # Reverse map: vertex index -> edge
        idx_to_edge = {v: e for e, v in vertex_to_idx.items()}

        colors = _dsatur_color(conflict_adj)
        n_colors = max(colors.values()) + 1 if colors else 0

        # Group vertices by color
        groups_dict: dict[int, list[tuple[int, int]]] = (
            collections.defaultdict(list)
        )
        for idx, col in colors.items():
            groups_dict[col].append(idx_to_edge[idx])

        groups = tuple(
            tuple(sorted(groups_dict[c], key=lambda e: (e[0], e[1])))
            for c in sorted(groups_dict)
        )

        return ParallelPatternResult(
            groups=groups,
            n_rounds=len(groups),
            chromatic_number=n_colors,
            source="auto",
        )

    def from_circuit(self, originir: str) -> ParallelPatternResult:
        """Analyze an OriginIR circuit and extract its parallel pattern.

        Parses all 2-qubit gates, builds a conflict graph from qubit overlap,
        and DSatur-colors it to get the minimal parallel schedule.

        Args:
            originir: Compiled circuit in OriginIR format.

        Returns:
            ParallelPatternResult describing the circuit's effective parallelism.
        """
        pairs = _parse_2q_gates_from_originir(originir)
        if not pairs:
            return ParallelPatternResult(
                groups=(),
                n_rounds=0,
                chromatic_number=0,
                source="circuit",
            )

        conflict_adj, _ = _build_conflict_graph_from_pairs(pairs)
        colors = _dsatur_color(conflict_adj)
        n_colors = max(colors.values()) + 1 if colors else 0

        groups_dict: dict[int, list[tuple[int, int]]] = (
            collections.defaultdict(list)
        )
        for idx, col in colors.items():
            groups_dict[col].append(pairs[idx])

        groups = tuple(
            tuple(sorted(groups_dict[c], key=lambda e: (e[0], e[1])))
            for c in sorted(groups_dict)
        )

        return ParallelPatternResult(
            groups=groups,
            n_rounds=len(groups),
            chromatic_number=n_colors,
            source="circuit",
        )
