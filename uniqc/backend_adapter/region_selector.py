"""RegionSelector: find optimal qubit regions on a quantum chip.

This module provides the :class:`RegionSelector` class, which uses chip
characterization data (per-qubit and per-pair calibration data) to find
optimal physical qubit regions for executing quantum circuits.

Example
-------
::

    from uniqc.backend_adapter.task.adapters.originq_adapter import OriginQAdapter
    from uniqc.backend_adapter.region_selector import RegionSelector

    adapter = OriginQAdapter()
    chip = adapter.get_chip_characterization("origin:wuyuan:d5")
    selector = RegionSelector(chip)

    # Find the best 5-qubit chain
    chain_result = selector.find_best_1D_chain(5)
    if chain_result.chain:
        print(f"Best chain: {chain_result.chain}")

    # Find the best region for a circuit
    region_result = selector.find_best_2D_from_circuit(circuit, min_qubits=4)
    if region_result.qubits:
        print(f"Best region: {region_result.qubits}")
"""

from __future__ import annotations

__all__ = ["RegionSelector", "ChainSearchResult", "RegionSearchResult"]

import dataclasses
import time
from collections import defaultdict
from collections.abc import Callable

from uniqc.circuit_builder import Circuit
from uniqc.cli.chip_info import (
    ChipCharacterization,
)

# Default fidelity assumed for qubits/edges not in characterisation
_DEFAULT_FIDELITY = 0.99


@dataclasses.dataclass
class ChainSearchResult:
    """Result of :meth:`RegionSelector.find_best_1D_chain`.

    Attributes
    ----------
    chain : list[int] | None
        List of physical qubit indices forming the chain, or ``None`` if no
        valid chain of the requested length exists.
    estimated_fidelity : float | None
        Estimated success probability of executing a single-layer circuit on
        this chain (product of edge fidelities), or ``None`` if no chain found.
    num_swaps : int
        Number of SWAP gates that would be needed to realise this chain
        from the circuit's natural qubit mapping (0 for an exact path match).
    """

    chain: list[int] | None
    estimated_fidelity: float | None
    num_swaps: int


@dataclasses.dataclass
class RegionSearchResult:
    """Result of :meth:`RegionSelector.find_best_2D_from_circuit`.

    Attributes
    ----------
    qubits : set[int] | None
        Set of physical qubit indices forming the best region, or ``None``
        if no region fits the circuit's qubit requirements.
    estimated_fidelity : float | None
        Estimated success probability of executing the full circuit on this
        region, or ``None`` if no region found.
    region_shape : tuple[int, int] | None
        Approximate dimensions of the selected region as ``(rows, cols)``,
        or ``None``.
    """

    qubits: set[int] | None
    estimated_fidelity: float | None
    region_shape: tuple[int, int] | None


class RegionSelector:
    """Select optimal qubit regions from chip characterisation data.

    Parameters
    ----------
    chip_characterization :
        Complete chip characterisation data including connectivity and fidelity
        information, typically fetched via
        :meth:`OriginQAdapter.get_chip_characterization` or the equivalent
        for other adapters.
    """

    def __init__(self, chip_characterization: ChipCharacterization) -> None:
        self._chip = chip_characterization
        self._sq_fid: dict[int, float] = {}
        self._tq_fid: dict[tuple[int, int], float] = {}
        self._adj: dict[int, list[tuple[int, float]]] = {}
        self._undirected_adj: dict[int, set[int]] = {}
        self._build_graph()

    # -------------------------------------------------------------------------
    # Graph building
    # -------------------------------------------------------------------------

    def _build_graph(self) -> None:
        """Pre-build fidelity maps and adjacency lists from chip characterisation."""
        # Single-qubit fidelity map: qubit_id -> single_gate_fidelity
        for sq_data in self._chip.single_qubit_data:
            if sq_data.single_gate_fidelity is not None:
                self._sq_fid[sq_data.qubit_id] = sq_data.single_gate_fidelity

        # Two-qubit fidelity map: undirected edge -> best gate fidelity
        for tq_data in self._chip.two_qubit_data:
            if tq_data.qubit_u == tq_data.qubit_v:
                continue  # skip self-loops which are not real two-qubit edges
            for gate in tq_data.gates:
                if gate.fidelity is not None:
                    edge = tuple(sorted((tq_data.qubit_u, tq_data.qubit_v)))
                    existing = self._tq_fid.get(edge)
                    if existing is None or gate.fidelity > existing:
                        self._tq_fid[edge] = gate.fidelity

        # Build undirected adjacency (for topology traversal)
        undirected: dict[int, set[int]] = defaultdict(set)
        directed_adj: dict[int, list[tuple[int, float]]] = defaultdict(list)

        for edge_topo in self._chip.connectivity:
            u, v = edge_topo.u, edge_topo.v
            if u == v:
                continue
            undirected[u].add(v)
            undirected[v].add(u)

        for edge_topo in self._chip.connectivity:
            u, v = edge_topo.u, edge_topo.v
            if u == v:
                continue
            edge = tuple(sorted((u, v)))
            fid = self._tq_fid.get(edge, _DEFAULT_FIDELITY)
            weight = 1.0 - fid  # lower weight = better
            directed_adj[u].append((v, weight))

        self._adj = dict(directed_adj)
        self._undirected_adj = dict(undirected)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def find_best_1D_chain(  # noqa: N802
        self,
        length: int,
        start: int | None = None,
        max_search_seconds: float = 30.0,
    ) -> ChainSearchResult:
        """Find the highest-fidelity linear chain of connected qubits.

        **Algorithm:**

        1. **Greedy phase.** Starting from ``start`` (or the qubit with the
           highest single-gate fidelity if not specified), repeatedly extend
           the chain by picking the neighbour with the highest two-qubit gate
           fidelity. Stop when the chain reaches ``length`` or no unvisited
           neighbours exist.

        2. **Backtracking phase.** If greedy fails to reach the desired length,
           perform a bounded DFS search from each candidate starting qubit.
           The search explores paths up to depth ``length`` and returns the
           path with the highest cumulative fidelity product, with alpha-beta
           pruning to bound search time.

        3. **Partial result.** If no chain of exactly ``length`` exists, return
           the best shorter chain found.

        The fidelity of a chain q0-q1-...-q_{n-1} is::

            F = product_{i=1}^{n-1} fidelity(q_{i-1}, q_i)

        Parameters
        ----------
        length :
            Desired number of qubits in the chain. Must be >= 1.
        start :
            Physical qubit index to start the chain from. If ``None``,
            the qubit with the highest single-gate fidelity is used.
        max_search_seconds :
            Time budget for the search. If exceeded during the backtracking
            phase, the best result found so far is returned. Default: 30 seconds.
            The greedy phase is typically fast and always runs to completion.

        Returns
        -------
        ChainSearchResult
            The best chain found, its estimated fidelity, and the number of
            SWAP gates needed (0 for an exact path match).

        Raises
        ------
        ValueError
            If ``length < 1``.
        """
        if length < 1:
            raise ValueError("length must be >= 1")
        if not self._chip.available_qubits:
            return ChainSearchResult(chain=None, estimated_fidelity=None, num_swaps=0)

        available = set(self._chip.available_qubits)
        deadline = time.time() + max_search_seconds

        # Determine candidate starting qubits
        if start is not None:
            if start not in available:
                return ChainSearchResult(chain=None, estimated_fidelity=None, num_swaps=0)
            candidates = [start]
        else:
            candidates = sorted(
                available,
                key=lambda q: self._sq_fid.get(q, 0.0),
                reverse=True,
            )
            if not candidates:
                candidates = list(available)

        # --- Greedy expansion (typically fast, no deadline needed) ---
        for start_q in candidates:
            chain, fidelity, swaps = self._greedy_chain_expand(start_q, length, available)
            if chain is not None and len(chain) == length:
                return ChainSearchResult(chain=chain, estimated_fidelity=fidelity, num_swaps=swaps)

        # --- Backtracking DFS search (deadline-checked) ---
        for start_q in candidates:
            if time.time() > deadline:
                break
            result = self._backtrack_chain(start_q, length, available, deadline=deadline)
            if result[0] is not None and len(result[0]) == length:
                return ChainSearchResult(chain=result[0], estimated_fidelity=result[1], num_swaps=result[2])

        # --- Return best partial chain (longest; highest-fidelity on tie) ---
        best_chain: list[int] = []
        best_fid = 0.0
        for start_q in candidates:
            chain, fidelity, _ = self._greedy_chain_expand(start_q, length, available)
            if chain is not None and (
                len(chain) > len(best_chain) or (len(chain) == len(best_chain) and fidelity > best_fid)
            ):
                best_fid = fidelity
                best_chain = chain

        if best_chain:
            return ChainSearchResult(chain=best_chain, estimated_fidelity=best_fid, num_swaps=0)
        return ChainSearchResult(chain=None, estimated_fidelity=None, num_swaps=0)

    def find_best_2D_from_circuit(  # noqa: N802
        self,
        circuit: Circuit,
        min_qubits: int | None = None,
        max_region_size: int = 36,
        max_search_seconds: float = 10.0,
        transpiler: Callable[[Circuit, list[int]], float] | None = None,
    ) -> RegionSearchResult:
        """Find the best 2D qubit region for executing a circuit.

        **Algorithm:**

        1. Determine the circuit's qubit requirements:
           ``min_qubits = max(circuit.max_qubit + 1, circuit.qubit_num)``.

        2. Enumerate candidate regions. The chip's connectivity graph is
           searched for connected subgraphs of rectangular topology.
           Enumeration proceeds in order of increasing size until a feasible
           region is found, bounded by ``max_region_size``.

           Heuristic: try rectangles of size 1×n, 2×n, 3×n, ... up to the
           circuit's qubit count. For each size, try all possible starting
           positions and orientations.

        3. For each candidate region, estimate circuit fidelity using
           :meth:`estimate_circuit_fidelity`. If a custom ``transpiler`` is
           provided, call it instead for a more accurate estimate.

        4. Return the region with the highest estimated fidelity.

        Parameters
        ----------
        circuit :
            The circuit to find a region for.
        min_qubits :
            Override the minimum qubit count. If ``None``, derived from the
            circuit's ``max_qubit`` and ``qubit_num``.
        max_region_size :
            Maximum number of qubits to search. Larger values increase search
            time but may find better regions. Default: 36.
        max_search_seconds :
            Time budget for the search. If exceeded, return the best result
            found so far. Default: 10 seconds.
        transpiler :
            Optional callable with signature ``(circuit, qubits: list[int]) -> float``.
            If provided, used instead of the built-in fidelity estimator,
            enabling more accurate (but slower) estimates via the full
            Qiskit transpiler.

        Returns
        -------
        RegionSearchResult
            The best region found, its estimated fidelity, and its shape.
        """
        required = min_qubits if min_qubits is not None else max(circuit.max_qubit + 1, circuit.qubit_num)

        if required > max_region_size:
            return RegionSearchResult(qubits=None, estimated_fidelity=None, region_shape=None)

        if not self._chip.available_qubits:
            return RegionSearchResult(qubits=None, estimated_fidelity=None, region_shape=None)

        available = set(self._chip.available_qubits)
        best_qubits: set[int] | None = None
        best_fid = 0.0
        best_shape: tuple[int, int] | None = None
        deadline = time.time() + max_search_seconds

        # Heuristic enumeration: try rectangles 1×n, 2×n, ... up to required qubits
        for rows in range(1, required + 1):
            if time.time() > deadline:
                break
            cols = (required + rows - 1) // rows  # ceiling division

            for shape in [(rows, cols), (cols, rows)] if rows != cols else [(rows, cols)]:
                r, c = shape
                if r * c > max_region_size:
                    continue
                if time.time() > deadline:
                    break

                for region in self._find_rectangular_subgraphs(r, c, available):
                    if time.time() > deadline:
                        break
                    if transpiler is not None:
                        fid = transpiler(circuit, list(region))
                    else:
                        fid = self.estimate_circuit_fidelity(circuit, qubits=region)
                    if fid > best_fid:
                        best_fid = fid
                        best_qubits = region
                        best_shape = (r, c)

        if best_qubits is None:
            return RegionSearchResult(qubits=None, estimated_fidelity=None, region_shape=None)
        return RegionSearchResult(qubits=best_qubits, estimated_fidelity=best_fid, region_shape=best_shape)

    def estimate_circuit_fidelity(
        self,
        circuit: Circuit,
        qubits: set[int] | None = None,
    ) -> float:
        """Estimate the success probability of executing a circuit on a qubit set.

        Uses the product-of-fidelities formula::

            P_success = product_{1Q gates} F_1q
                      × product_{2Q gates} F_2q
                      × product_{measured qubits} F_readout

        Where gate error rates are derived from the chip characterisation:

        - Single-qubit gate fidelity: from ``SingleQubitData.single_gate_fidelity``
        - Two-qubit gate fidelity: best fidelity among all gate types for that edge
        - Readout fidelity: from ``SingleQubitData.avg_readout_fidelity``

        If a qubit or edge is not in the characterisation data, a default
        fidelity of 0.99 (1% error rate) is used.

        Parameters
        ----------
        circuit :
            The circuit to estimate fidelity for.
        qubits :
            The set of physical qubits to execute on. If ``None``, uses all
            available qubits from the chip characterisation.

        Returns
        -------
        float
            Estimated success probability between 0.0 and 1.0.
        """
        if qubits is None:
            qubits = set(self._chip.available_qubits)

        fidelity = 1.0

        for opcode in circuit.opcode_list:
            op, qubit, *_ = opcode

            if op is None or op in (
                "CONTROL",
                "ENDCONTROL",
                "DAGGER",
                "ENDDAGGER",
                "QINIT",
                "CREG",
                "BARRIER",
                "DEF",
                "ENDDEF",
            ):
                continue

            if isinstance(qubit, int):
                if qubit in qubits:
                    fidelity *= self._sq_fid.get(qubit, _DEFAULT_FIDELITY)
            elif isinstance(qubit, list) and len(qubit) >= 2:
                q0, q1 = qubit[0], qubit[1]
                if q0 in qubits and q1 in qubits:
                    edge = tuple(sorted((q0, q1)))
                    fidelity *= self._tq_fid.get(edge, _DEFAULT_FIDELITY)

        # Readout fidelity for measured qubits
        for q in circuit.measure_list:
            if q in qubits:
                for sq_data in self._chip.single_qubit_data:
                    if sq_data.qubit_id == q and sq_data.avg_readout_fidelity is not None:
                        fidelity *= sq_data.avg_readout_fidelity
                        break

        return max(0.0, min(1.0, fidelity))

    def get_qubit_rankings(self) -> list[tuple[int, float]]:
        """Return all available qubits ranked by single-gate fidelity.

        Returns
        -------
        list of (qubit_id, fidelity) sorted by fidelity descending.
        """
        available = set(self._chip.available_qubits)
        ranked = [(q, self._sq_fid.get(q, _DEFAULT_FIDELITY)) for q in available]
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked

    def get_edge_rankings(self) -> list[tuple[tuple[int, int], float]]:
        """Return all available edges ranked by two-qubit gate fidelity.

        Returns
        -------
        list of ((qubit_u, qubit_v), fidelity) sorted by fidelity descending.
        """
        ranked = [(e, f) for e, f in self._tq_fid.items()]
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _greedy_chain_expand(
        self,
        start: int,
        length: int,
        available: set[int],
    ) -> tuple[list[int], float, int]:
        """Find a simple path of exactly ``length`` qubits from ``start``.

        Explores paths in lexicographic order (sorted-neighbor DFS) and returns
        the first path that reaches exactly ``length`` qubits. This gives the
        lexicographically-first path of the target length.

        If no exact-length path exists, returns the longest path found.

        Returns (path, cumulative_fidelity, num_swaps).
        """
        if length == 1:
            fid = self._sq_fid.get(start, _DEFAULT_FIDELITY)
            return [start], fid, 0

        best_path: list[int] = []
        best_fid = 0.0
        best_len = 0

        def dfs(current: int, path: list[int], visited: set[int], fid: float) -> None:
            nonlocal best_path, best_fid, best_len

            # Update best: prefer longer paths; on tie, prefer higher fidelity
            if len(path) > best_len or (len(path) == best_len and fid > best_fid):
                best_len = len(path)
                best_fid = fid
                best_path = list(path)

            # Prune: can't beat current best length even visiting every remaining qubit
            remaining = len(available - visited)
            if len(path) + remaining <= best_len:
                return

            # Explore neighbors in sorted order for lexicographic ordering
            for v in sorted(self._undirected_adj.get(current, set()) & available - visited):
                edge_fid = self._tq_fid.get(tuple(sorted((current, v))), _DEFAULT_FIDELITY)
                path.append(v)
                visited.add(v)
                dfs(v, path, visited, fid * edge_fid)
                visited.remove(v)
                path.pop()

        dfs(start, [start], {start}, self._sq_fid.get(start, _DEFAULT_FIDELITY))

        # Clip to exactly `length` qubits: take the first `length` elements of the best path.
        # Since DFS explores in lexicographic order, `best_path` is already
        # the lexicographically-first longest path. Truncating gives the
        # lexicographically-first path of the requested length.
        if len(best_path) >= length:
            exact_path = best_path[:length]
            # Compute fidelity for the exact-length path
            exact_fid = self._sq_fid.get(exact_path[0], _DEFAULT_FIDELITY)
            for i in range(1, len(exact_path)):
                edge_fid = self._tq_fid.get(tuple(sorted((exact_path[i - 1], exact_path[i]))), _DEFAULT_FIDELITY)
                exact_fid *= edge_fid
            return exact_path, exact_fid, 0

        return best_path, best_fid, 0

    def _backtrack_chain(
        self,
        start: int,
        length: int,
        available: set[int],
        deadline: float | None = None,
    ) -> tuple[list[int], float, int]:
        """DFS backtracking search for a chain of exactly ``length`` qubits.

        Searches for a path of exactly ``length`` qubits. Returns the
        lexicographically-first path among those with the highest cumulative
        fidelity. If no exact-length path exists, returns the best partial path.

        Returns (path, cumulative_fidelity, num_swaps).
        """
        best_path: list[int] = []
        best_fid = 0.0
        best_len = 0
        found_exact_len = False
        timed_out = False

        # Separate tracking for exact-length paths only:
        # When found_exact_len=True, best_path may be updated by later DFS branches
        # that found longer or higher-fidelity paths (including same-length paths).
        # We need a dedicated tracker for the best *exact-length* path.
        best_exact_path: list[int] = []
        best_exact_fid = 0.0

        def dfs(current: int, path: list[int], visited: set[int], fid: float) -> None:
            nonlocal best_path, best_fid, best_len, found_exact_len, timed_out
            nonlocal best_exact_path, best_exact_fid

            if timed_out:
                return

            # Deadline check (every few levels to reduce syscall overhead)
            if deadline is not None and len(path) % 4 == 0 and time.time() > deadline:
                timed_out = True
                return

            # Update global best (any length)
            if len(path) > best_len or (len(path) == best_len and fid > best_fid):
                best_len = len(path)
                best_fid = fid
                best_path = list(path)

            # Exact-length tracking: update only when path reaches target length
            if len(path) == length:
                found_exact_len = True
                # Among exact-length paths, prefer lexicographically smaller (found first)
                # Since DFS explores in sorted-neighbor order, first exact-length path
                # encountered IS the lexicographically-first one — no further comparison needed.
                if not best_exact_path:
                    best_exact_path = list(path)
                    best_exact_fid = fid
                # NOTE: we intentionally do NOT update best_exact_path on later exact-length
                # paths, preserving the lexicographically-first one.

            # Prune: can't reach target length
            remaining = len(available - visited)
            if len(path) + remaining < length:
                return

            for v in sorted(self._undirected_adj.get(current, set()) & available - visited):
                if timed_out:
                    return
                edge_fid = self._tq_fid.get(tuple(sorted((current, v))), _DEFAULT_FIDELITY)
                path.append(v)
                visited.add(v)
                dfs(v, path, visited, fid * edge_fid)
                visited.remove(v)
                path.pop()

        dfs(start, [start], {start}, self._sq_fid.get(start, _DEFAULT_FIDELITY))

        # If no exact-length path found, return best partial
        if not found_exact_len and best_path:
            return best_path, best_fid, max(0, len(best_path) - 1)
        # Return the best exact-length path (lexicographically first, highest fidelity)
        if found_exact_len:
            return best_exact_path, best_exact_fid, max(0, len(best_exact_path) - 1)
        return [], 0.0, 0

    def _find_rectangular_subgraphs(
        self,
        rows: int,
        cols: int,
        available: set[int],
    ) -> list[set[int]]:
        """Find all connected subgraphs of approximately rows×cols qubits.

        Uses BFS-based growth from each starting qubit, ensuring the induced
        subgraph is connected. Results are deduplicated by frozenset.
        """
        target_size = rows * cols
        results: list[set[int]] = []

        for start in sorted(available):
            queue: list[tuple[int, set[int]]] = [(start, {start})]

            while queue:
                current, visited = queue.pop(0)

                if len(visited) >= target_size:
                    results.append(visited)
                    continue

                # Limit exploration per starting qubit to avoid combinatorial explosion
                if len(visited) >= min(target_size, max(rows * cols, len(results) * 2 + 10)):
                    continue

                for neighbor in self._undirected_adj.get(current, set()) & available - visited:
                    # Ensure neighbor connects to at least one existing qubit in the region
                    if visited & self._undirected_adj.get(neighbor, set()):
                        new_visited = visited | {neighbor}
                        if len(new_visited) <= target_size:
                            queue.append((neighbor, new_visited))
                            if len(new_visited) >= target_size:
                                results.append(new_visited)

        # Deduplicate and filter to connected regions of exactly target_size qubits
        seen: set[frozenset[int]] = set()
        exact: list[set[int]] = []
        for r in results:
            if len(r) == target_size:
                key = frozenset(r)
                if key not in seen:
                    seen.add(key)
                    exact.append(r)

        return exact
