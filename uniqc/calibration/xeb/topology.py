"""Chip topology utilities for parallel-CZ XEB calibration.

These helpers wrap a :class:`uniqc.cli.chip_info.ChipCharacterization`
into a lightweight view (per-qubit / per-pair fidelities + adjacency)
that the parallel-CZ XEB workflow uses to pick a region and build
parallel CZ patterns.

The primitives here are *generic* — no UU15 or paper-specific logic.

Public API
----------
* :class:`ChipTopologyView` — adapter over ``ChipCharacterization``
* :class:`Region` — connected qubit subset + induced edges
* :func:`pick_region` — fidelity-weighted greedy seed-and-grow
* :func:`pick_chain_region` — best chord-free linear chain
* :func:`parallel_patterns` — DSatur edge-coloring of a list of edges
* :func:`three_color_chip` — chip-wide partition into ``≤max_K`` matchings
"""

from __future__ import annotations

import dataclasses
import math
import random
import statistics
from collections import defaultdict
from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uniqc.cli.chip_info import ChipCharacterization

from uniqc.calibration.xeb.patterns import ParallelPatternGenerator

__all__ = [
    "ChipTopologyView",
    "Region",
    "pick_region",
    "pick_chain_region",
    "parallel_patterns",
    "three_color_chip",
]


# ---------------------------------------------------------------------------
# Chip view
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class ChipTopologyView:
    """Lightweight per-qubit / per-pair fidelity view over a chip.

    ``e_1q[q]``, ``e_ro[q]`` and ``e_2q[(min(a,b), max(a,b))]`` are
    error rates in ``[0, 1]``. Missing entries fall back to safe
    defaults (1e-3 single-qubit, 1e-2 readout, chip-wide 2q-median).
    """

    enabled_qubits: tuple[int, ...]
    coupling_map: tuple[tuple[int, int], ...]
    e_1q: dict[int, float]
    e_2q: dict[tuple[int, int], float]
    e_ro: dict[int, float]
    notes: tuple[str, ...] = ()

    @classmethod
    def from_chip_characterization(
        cls,
        chip: ChipCharacterization,
        *,
        enabled_qubits: Iterable[int] | None = None,
    ) -> ChipTopologyView:
        """Build a view from a ``ChipCharacterization``.

        ``enabled_qubits`` defaults to ``chip.available_qubits``.
        """
        if enabled_qubits is None:
            enabled = tuple(int(q) for q in chip.available_qubits)
        else:
            enabled = tuple(int(q) for q in enabled_qubits)
        enabled_set = set(enabled)
        coupling_map = tuple(
            sorted(
                {
                    (min(int(t.u), int(t.v)), max(int(t.u), int(t.v)))
                    for t in chip.connectivity
                    if int(t.u) in enabled_set and int(t.v) in enabled_set and t.u != t.v
                }
            )
        )
        e_1q: dict[int, float] = {}
        e_ro: dict[int, float] = {}
        for s in chip.single_qubit_data:
            if int(s.qubit_id) not in enabled_set:
                continue
            f1 = s.single_gate_fidelity if s.single_gate_fidelity is not None else 0.999
            fro = s.avg_readout_fidelity if s.avg_readout_fidelity is not None else 0.99
            e_1q[int(s.qubit_id)] = max(0.0, 1.0 - float(f1))
            e_ro[int(s.qubit_id)] = max(0.0, 1.0 - float(fro))
        # Defaults for any missing qubit
        for q in enabled:
            e_1q.setdefault(q, 1e-3)
            e_ro.setdefault(q, 1e-2)

        e_2q, notes = _per_pair_2q_error(chip, coupling_map)
        return cls(
            enabled_qubits=enabled,
            coupling_map=coupling_map,
            e_1q=e_1q,
            e_2q=e_2q,
            e_ro=e_ro,
            notes=tuple(notes),
        )

    def two_qubit_error(self, a: int, b: int) -> float:
        key = (min(int(a), int(b)), max(int(a), int(b)))
        return self.e_2q[key]

    def adjacency(self) -> dict[int, set[int]]:
        adj: dict[int, set[int]] = defaultdict(set)
        for a, b in self.coupling_map:
            adj[a].add(b)
            adj[b].add(a)
        return adj


def _per_pair_2q_error(
    chip: ChipCharacterization,
    coupling_map: Iterable[tuple[int, int]],
) -> tuple[dict[tuple[int, int], float], list[str]]:
    """Build per-edge 2q error dict from a ChipCharacterization.

    Strategy:
    1. If any TwoQubitData record has ``qubit_u != qubit_v`` and at least
       one fidelity, use it directly per pair.
    2. Otherwise (some uniqc cache shapes), fall back to the median of
       all available 2q fidelities and tag the topology view notes.
    """
    notes: list[str] = []
    per_pair: dict[tuple[int, int], float] = {}
    for tq in chip.two_qubit_data:
        if tq.qubit_u == tq.qubit_v:
            continue
        for g in tq.gates:
            if g.fidelity is None:
                continue
            err = max(0.0, 1.0 - float(g.fidelity))
            key = (min(int(tq.qubit_u), int(tq.qubit_v)), max(int(tq.qubit_u), int(tq.qubit_v)))
            per_pair[key] = err
    edges = list(coupling_map)
    if per_pair:
        # Fill in missing edges with chip-wide median if any.
        if len(per_pair) < len(edges):
            present_vals = list(per_pair.values())
            med = statistics.median(present_vals) if present_vals else 1e-2
            n_filled = 0
            for a, b in edges:
                key = (min(a, b), max(a, b))
                if key not in per_pair:
                    per_pair[key] = float(med)
                    n_filled += 1
            if n_filled:
                notes.append(
                    f"{n_filled}/{len(edges)} edges had no 2q fidelity in cache; filled with median err={med:.6f}"
                )
        return per_pair, notes

    # Fallback: aggregate all 2q fidelities (some caches encode chip-wide
    # 2q numbers as TwoQubitData with qubit_u == qubit_v).
    all_fids: list[float] = []
    for tq in chip.two_qubit_data:
        for g in tq.gates:
            if g.fidelity is not None:
                all_fids.append(float(g.fidelity))
    if not all_fids:
        if not edges:
            return {}, notes
        notes.append("no 2q fidelity data in cache; assuming err=1e-2 for every edge")
        return {(min(a, b), max(a, b)): 1e-2 for (a, b) in edges}, notes
    med = statistics.median(all_fids)
    err = max(0.0, 1.0 - float(med))
    notes.append(
        "per-edge 2q fidelity unavailable in cache; using chip-wide median "
        f"fid={med:.6f} (n={len(all_fids)}) as a constant fallback"
    )
    return {(min(a, b), max(a, b)): err for (a, b) in edges}, notes


# ---------------------------------------------------------------------------
# Region selection
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class Region:
    """A connected induced subgraph of a chip's coupling graph."""

    qubits: tuple[int, ...]
    edges: tuple[tuple[int, int], ...]
    score: float

    def __post_init__(self) -> None:
        qset = set(self.qubits)
        for a, b in self.edges:
            if a not in qset or b not in qset:
                raise ValueError(f"Edge {(a, b)} references qubit not in region {self.qubits}")


def _is_connected(qubits: Iterable[int], adj: dict[int, set[int]]) -> bool:
    qs = list(qubits)
    if not qs:
        return False
    qset = set(qs)
    seen = {qs[0]}
    stack = [qs[0]]
    while stack:
        u = stack.pop()
        for v in adj.get(u, ()):
            if v in qset and v not in seen:
                seen.add(v)
                stack.append(v)
    return len(seen) == len(qset)


def _induced_edges(qubits: Iterable[int], adj: dict[int, set[int]]) -> list[tuple[int, int]]:
    qset = set(qubits)
    out: set[tuple[int, int]] = set()
    for u in qset:
        for v in adj.get(u, ()):
            if v in qset and u < v:
                out.add((u, v))
    return sorted(out)


def _region_score(qubits: Iterable[int], view: ChipTopologyView, adj: dict[int, set[int]]) -> float:
    qubits = list(qubits)
    s = 0.0
    for v in qubits:
        f_v = max(1e-6, 1.0 - view.e_1q.get(v, 1.0))
        f_ro = max(1e-6, 1.0 - view.e_ro.get(v, 1.0))
        s += math.log(f_v) + math.log(f_ro)
    for a, b in _induced_edges(qubits, adj):
        try:
            f_e = max(1e-6, 1.0 - view.two_qubit_error(a, b))
        except KeyError:
            f_e = 1e-6
        s += math.log(f_e)
    return s


def _bfs_grow(seed: int, n: int, adj: dict[int, set[int]], view: ChipTopologyView) -> list[int]:
    chosen = [seed]
    chosen_set = {seed}
    while len(chosen) < n:
        cands: set[int] = set()
        for q in chosen:
            for nb in adj.get(q, ()):
                if nb not in chosen_set:
                    cands.add(nb)
        if not cands:
            break

        def cand_score(c: int) -> float:
            f_v = max(1e-6, 1.0 - view.e_1q.get(c, 1.0))
            f_ro = max(1e-6, 1.0 - view.e_ro.get(c, 1.0))
            s = math.log(f_v) + math.log(f_ro)
            for q in chosen:
                if q in adj.get(c, ()):
                    try:
                        f_e = max(1e-6, 1.0 - view.two_qubit_error(c, q))
                    except KeyError:
                        f_e = 1e-6
                    s += math.log(f_e)
            return s

        best = max(cands, key=cand_score)
        chosen.append(best)
        chosen_set.add(best)
    return chosen


def _annealing_polish(
    view: ChipTopologyView,
    adj: dict[int, set[int]],
    initial: list[int],
    *,
    seed: int,
    iterations: int = 200,
) -> list[int]:
    rng = random.Random(seed)
    cur = list(initial)
    cur_set = set(cur)
    cur_score = _region_score(cur, view, adj)
    if len(cur) < 2:
        return cur
    for _ in range(iterations):
        v = rng.choice(cur)
        outside = [u for q in cur for u in adj.get(q, ()) if u not in cur_set]
        if not outside:
            break
        u = rng.choice(outside)
        new_set = (cur_set - {v}) | {u}
        if not _is_connected(new_set, adj):
            continue
        new_list = list(new_set)
        new_score = _region_score(new_list, view, adj)
        if new_score > cur_score:
            cur, cur_set, cur_score = new_list, new_set, new_score
    return cur


def pick_region(view: ChipTopologyView, n: int, *, seed: int = 0) -> Region:
    """Select ``n`` connected qubits maximising ``Σ log f_v + Σ log f_e``.

    Uses greedy seed-and-grow over the highest-fidelity vertex, then a
    seed-deterministic SA polish. Raises if no connected region of the
    requested size exists.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    if n > len(view.enabled_qubits):
        raise ValueError(f"Requested {n} qubits but only {len(view.enabled_qubits)} enabled.")
    adj = view.adjacency()
    sorted_seeds = sorted(
        view.enabled_qubits,
        key=lambda v: -((1.0 - view.e_1q.get(v, 1.0)) * (1.0 - view.e_ro.get(v, 1.0))),
    )
    rng = random.Random(seed)
    candidates: list[tuple[float, list[int]]] = []
    for s in sorted_seeds[: max(8, min(32, len(sorted_seeds)))]:
        grown = _bfs_grow(s, n, adj, view)
        if len(grown) != n or not _is_connected(grown, adj):
            continue
        polished = _annealing_polish(view, adj, grown, seed=rng.randint(0, 1_000_000))
        candidates.append((_region_score(polished, view, adj), polished))
    if not candidates:
        raise RuntimeError(f"No connected region of size {n} found on {len(view.enabled_qubits)} qubits.")
    score, best = max(candidates, key=lambda t: t[0])
    qubits = tuple(sorted(best))
    edges = tuple(_induced_edges(qubits, adj))
    return Region(qubits=qubits, edges=edges, score=score)


def pick_chain_region(
    view: ChipTopologyView,
    length: int,
    *,
    forced_qubits: Iterable[int] | None = None,
) -> Region:
    """Best chord-free linear chain ``q0 — q1 — … — q_{L-1}`` of length ``length``.

    A "chord-free" chain has only the consecutive edges in its induced
    subgraph (no shortcuts). Useful for MPS-friendly experiments.

    If ``forced_qubits`` is given, validate it as a chain and return it
    directly. Otherwise enumerate simple paths.
    """
    adj = view.adjacency()
    enabled = set(view.enabled_qubits)
    if forced_qubits is not None:
        qs = tuple(int(q) for q in forced_qubits)
        if len(qs) != length:
            raise ValueError(f"forced_qubits has length {len(qs)} but length={length} requested")
        for i in range(length - 1):
            if qs[i + 1] not in adj.get(qs[i], set()):
                raise ValueError(f"forced chain {qs}: qubits {qs[i]} and {qs[i + 1]} are not adjacent")
        induced = _induced_edges(qs, adj)
        chain_edges = tuple(sorted((min(qs[i], qs[i + 1]), max(qs[i], qs[i + 1])) for i in range(length - 1)))
        if set(induced) != set(chain_edges):
            extra = set(induced) - set(chain_edges)
            raise ValueError(f"forced chain {qs} is not chord-free; extra induced edges: {extra}")
        return Region(qubits=qs, edges=chain_edges, score=_region_score(qs, view, adj))

    best: tuple[float, tuple[int, ...]] | None = None
    cap = 1_000_000
    counter = 0
    for start in sorted(enabled):
        stack: list[tuple[tuple[int, ...], set[int]]] = [((start,), {start})]
        while stack:
            path, used = stack.pop()
            counter += 1
            if counter > cap:
                break
            if len(path) == length:
                induced = _induced_edges(path, adj)
                expected = {(min(a, b), max(a, b)) for a, b in zip(path, path[1:])}
                if {(min(a, b), max(a, b)) for a, b in induced} != expected:
                    continue
                s = _region_score(path, view, adj)
                if best is None or s > best[0]:
                    best = (s, path)
                continue
            tail = path[-1]
            for nb in sorted(adj.get(tail, ())):
                if nb in used or nb not in enabled:
                    continue
                stack.append((path + (nb,), used | {nb}))
        if counter > cap:
            break
    if best is None:
        raise RuntimeError(f"no chord-free chain of length {length} found")
    qs = best[1]
    chain_edges = tuple(sorted((min(qs[i], qs[i + 1]), max(qs[i], qs[i + 1])) for i in range(length - 1)))
    return Region(qubits=qs, edges=chain_edges, score=best[0])


# ---------------------------------------------------------------------------
# Parallel pattern coloring
# ---------------------------------------------------------------------------


def parallel_patterns(edges: Sequence[tuple[int, int]], *, max_K: int = 8) -> tuple[tuple[tuple[int, int], ...], ...]:
    """DSatur edge-coloring of ``edges`` into edge-disjoint matchings.

    Returns a tuple of patterns ``(P_0, ..., P_{K-1})``. Each pattern is
    a tuple of ``(a, b)`` edges with no qubit appearing twice in the
    same pattern. If the maximum vertex degree exceeds ``max_K`` the
    coloring may spill an edge into a non-empty class — increase
    ``max_K`` to ``Δ + 1`` to avoid that.
    """
    edge_list = [(min(int(a), int(b)), max(int(a), int(b))) for (a, b) in edges]
    if not edge_list:
        return ()
    gen = ParallelPatternGenerator(edge_list)
    result = gen.auto_generate()
    return result.groups


def three_color_chip(view: ChipTopologyView, *, max_K: int = 3) -> tuple[tuple[tuple[int, int], ...], ...]:
    """Edge-color the chip's coupling map into ``≤max_K`` parallel patterns.

    Most superconducting chips have max-degree ≤ 3, so ``max_K = 3`` is
    sufficient. For higher-degree chips, pass ``max_K = Δ + 1`` (where
    ``Δ`` is the max vertex degree).
    """
    return parallel_patterns(view.coupling_map, max_K=max_K)
