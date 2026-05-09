"""High-level XEB workflow combining calibration, readout EM, and fidelity fitting.

Chip-agnostic: works with any backend supported by UnifiedQuantum.
For WK180-specific usage, see ``examples/wk180/xeb.py``.
"""

from __future__ import annotations

from typing import Any

from uniqc._error_hints import format_enriched_message

__all__ = [
    "run_1q_xeb_workflow",
    "run_2q_xeb_workflow",
    "run_parallel_xeb_workflow",
    "run_parallel_cz_xeb_workflow",
]


def _get_adapter(backend: str, **kwargs) -> Any:
    """Get a QuantumAdapter for the given backend name.

    Args:
        backend: Backend identifier, e.g. ``"local"``,
            ``"dummy:local:simulator"``, ``"dummy:originq:WK_C180"``,
            ``"originq:WK_C180"``. Any malformed identifier raises
            :class:`ValueError`; missing SDK / chip cache problems raise
            :class:`MissingDependencyError` /
            :class:`BackendPreflightError` respectively. There are no
            silent fallbacks.
    """
    from uniqc.backend_adapter.preflight import parse_backend_target
    from uniqc.backend_adapter.task.adapters import (
        DummyAdapter,
        OriginQAdapter,
        QuafuAdapter,
    )

    target = parse_backend_target(backend)
    if target.kind in ("local", "local_topology", "local_mps", "dummy_provider"):
        from uniqc.backend_adapter.dummy_backend import dummy_adapter_kwargs

        return DummyAdapter(**dummy_adapter_kwargs(backend, **kwargs))
    if target.provider == "originq":
        return OriginQAdapter(backend_name=target.chip_name or "")
    if target.provider == "quafu":
        return QuafuAdapter(**kwargs)
    raise ValueError(
        f"Backend identifier {backend!r} (kind={target.kind!r}, "
        f"provider={target.provider!r}) has no adapter wired in this "
        "workflow. Use 'local', 'dummy:local:simulator', "
        "'dummy:<provider>:<chip>', or '<provider>:<chip>'."
    )


def run_1q_xeb_workflow(
    backend: str = "dummy:local:simulator",
    qubits: list[int] | None = None,
    depths: list[int] | None = None,
    n_circuits: int = 50,
    shots: int = 1000,
    use_readout_em: bool = True,
    max_age_hours: float = 24.0,
    chip_characterization: Any = None,
    noise_model: dict[str, Any] | None = None,
    seed: int | None = None,
    cache_dir: str | None = None,
) -> dict[int, Any]:
    """Run 1-qubit XEB on one or more qubits.

    Args:
        backend: Backend name (e.g. "dummy", "originq:wuyuan:wk180").
        qubits: List of qubit indices to benchmark. Defaults to [0, 1, 2].
        depths: List of circuit depths. Defaults to [5, 10, 20, 50, 100].
        n_circuits: Number of random circuits per depth.
        shots: Shots per circuit.
        use_readout_em: Whether to apply readout EM before fidelity computation.
        max_age_hours: Maximum age of cached calibration data (hours).
        chip_characterization: Optional ChipCharacterization for noise-aware simulation.
        noise_model: Optional explicit DummyAdapter noise model.
        seed: Random seed for circuit generation.

    Returns:
        Dict mapping qubit index → XEBResult.
    """
    from uniqc.calibration.readout import ReadoutCalibrator
    from uniqc.calibration.xeb.benchmarker import XEBenchmarker
    from uniqc.qem import ReadoutEM

    if depths is None:
        depths = [5, 10, 20, 50, 100]
    if qubits is None:
        qubits = [0, 1, 2]

    adapter_kwargs: dict[str, Any] = {}
    if chip_characterization is not None:
        adapter_kwargs["chip_characterization"] = chip_characterization
    if noise_model is not None:
        adapter_kwargs["noise_model"] = noise_model

    adapter = _get_adapter(backend, **adapter_kwargs)

    # Optionally set up readout EM
    readout_em = None
    if use_readout_em:
        ReadoutCalibrator(adapter=adapter, shots=shots, cache_dir=cache_dir).calibrate_qubits(qubits)
        readout_em = ReadoutEM(
            adapter=adapter,
            max_age_hours=max_age_hours,
            cache_dir=cache_dir,
            shots=shots,
        )

    benchmarker = XEBenchmarker(
        adapter=adapter,
        shots=shots,
        readout_em=readout_em,
        seed=seed,
        cache_dir=cache_dir,
    )

    results = {}
    for q in qubits:
        results[q] = benchmarker.run_1q(q, depths, n_circuits)
    return results


def run_2q_xeb_workflow(
    backend: str = "dummy:local:simulator",
    pairs: list[tuple[int, int]] | None = None,
    depths: list[int] | None = None,
    n_circuits: int = 50,
    shots: int = 1000,
    use_readout_em: bool = True,
    max_age_hours: float = 24.0,
    chip_characterization: Any = None,
    noise_model: dict[str, Any] | None = None,
    seed: int | None = None,
    entangler_gates: dict[tuple[int, int], str] | None = None,
    cache_dir: str | None = None,
) -> dict[tuple[int, int], Any]:
    """Run 2-qubit XEB on one or more qubit pairs.

    Args:
        backend: Backend name.
        pairs: List of (u, v) qubit pairs. Defaults to [(0,1), (1,2)].
        depths: List of circuit depths.
        n_circuits: Number of random circuits per depth.
        shots: Shots per circuit.
        use_readout_em: Whether to apply readout EM before fidelity computation.
        max_age_hours: Maximum age of cached calibration data.
        chip_characterization: Optional ChipCharacterization.
        noise_model: Optional explicit DummyAdapter noise model.
        seed: Random seed.
        entangler_gates: Per-pair 2-qubit gate name override.

    Returns:
        Dict mapping (u, v) → XEBResult.
    """
    from uniqc.calibration.readout import ReadoutCalibrator
    from uniqc.calibration.xeb.benchmarker import XEBenchmarker
    from uniqc.qem import ReadoutEM

    if depths is None:
        depths = [5, 10, 20, 50]
    if pairs is None:
        pairs = [(0, 1), (1, 2)]

    adapter_kwargs: dict[str, Any] = {}
    if chip_characterization is not None:
        adapter_kwargs["chip_characterization"] = chip_characterization
    if noise_model is not None:
        adapter_kwargs["noise_model"] = noise_model

    adapter = _get_adapter(backend, **adapter_kwargs)

    readout_em = None
    if use_readout_em:
        ReadoutCalibrator(adapter=adapter, shots=shots, cache_dir=cache_dir).calibrate_pairs(pairs)
        readout_em = ReadoutEM(
            adapter=adapter,
            max_age_hours=max_age_hours,
            cache_dir=cache_dir,
            shots=shots,
        )

    benchmarker = XEBenchmarker(
        adapter=adapter,
        shots=shots,
        readout_em=readout_em,
        seed=seed,
        cache_dir=cache_dir,
    )

    results = {}
    for pair in pairs:
        u, v = pair
        # Pick entangler gate
        gate = entangler_gates.get(pair, entangler_gates.get((v, u), "CNOT")) if entangler_gates else "CNOT"
        results[pair] = benchmarker.run_2q(u, v, depths, n_circuits, gate)
    return results


def run_parallel_xeb_workflow(
    backend: str = "dummy:local:simulator",
    chip_characterization: Any = None,
    depths: list[int] | None = None,
    n_circuits: int = 50,
    shots: int = 1000,
    use_readout_em: bool = True,
    max_age_hours: float = 24.0,
    noise_model: dict[str, Any] | None = None,
    seed: int | None = None,
    target_qubits: list[int] | None = None,
    cache_dir: str | None = None,
) -> dict[str, Any]:
    """Run full-chip parallel 2-qubit XEB using auto-generated patterns.

    The chip topology is read from ``chip_characterization.connectivity``.
    All edges in the topology are grouped into parallel rounds using DSatur coloring,
    then XEB is run on all pairs simultaneously in each round.

    Args:
        backend: Backend name.
        chip_characterization: ``ChipCharacterization`` providing topology.
        depths: List of circuit depths.
        n_circuits: Number of circuits per depth.
        shots: Shots per circuit.
        use_readout_em: Apply readout EM.
        max_age_hours: Maximum calibration data age.
        noise_model: Optional explicit DummyAdapter noise model.
        seed: Random seed.
        target_qubits: Optional subset of qubits to include (uses full topology if None).

    Returns:
        Dict with keys: ``patterns`` (ParallelPatternResult),
        ``results`` (per-pair XEBResult), ``pairs``.
    """
    from uniqc.calibration.readout import ReadoutCalibrator
    from uniqc.calibration.xeb.benchmarker import XEBenchmarker
    from uniqc.calibration.xeb.patterns import ParallelPatternGenerator
    from uniqc.qem import ReadoutEM

    if chip_characterization is None:
        raise ValueError(format_enriched_message("chip_characterization is required for parallel XEB", "circuit_validation"))

    if depths is None:
        depths = [5, 10, 20]

    # Build topology
    edges = [
        (e.u, e.v) for e in chip_characterization.connectivity
    ]
    if target_qubits is not None:
        target_set = set(target_qubits)
        edges = [(u, v) for u, v in edges if u in target_set and v in target_set]

    if not edges:
        raise ValueError(format_enriched_message("No edges found in chip topology", "circuit_validation"))

    # Auto-generate parallel patterns
    gen = ParallelPatternGenerator(edges)
    pattern = gen.auto_generate()

    # Build per-pair entangler gate map from chip characterization
    entangler_gates: dict[tuple[int, int], str] = {}
    for tq_data in chip_characterization.two_qubit_data:
        u, v = tq_data.qubit_u, tq_data.qubit_v
        # Pick highest-fidelity gate
        best_gate, best_fid = "CNOT", -1.0
        for gate_data in tq_data.gates:
            if gate_data.fidelity is not None and gate_data.fidelity > best_fid:
                best_fid = gate_data.fidelity
                best_gate = gate_data.gate.upper()
        for pair in [(u, v), (v, u)]:
            if pair in edges:
                entangler_gates[pair] = best_gate

    adapter_kwargs: dict[str, Any] = {"chip_characterization": chip_characterization}
    if noise_model is not None:
        adapter_kwargs["noise_model"] = noise_model
    adapter = _get_adapter(backend, **adapter_kwargs)

    readout_em = None
    if use_readout_em:
        ReadoutCalibrator(adapter=adapter, shots=shots, cache_dir=cache_dir).calibrate_pairs(edges)
        readout_em = ReadoutEM(
            adapter=adapter,
            max_age_hours=max_age_hours,
            cache_dir=cache_dir,
            shots=shots,
        )

    benchmarker = XEBenchmarker(
        adapter=adapter,
        shots=shots,
        readout_em=readout_em,
        seed=seed,
        cache_dir=cache_dir,
    )

    results = {}
    for depth in depths:
        for pair in edges:
            if pair not in results:
                results[pair] = []
            gate = entangler_gates.get(pair, entangler_gates.get((pair[1], pair[0]), "CNOT"))
            r = benchmarker.run_2q(pair[0], pair[1], [depth], n_circuits, gate)
            results[pair].append(r)

    return {
        "patterns": pattern,
        "results": results,
        "pairs": edges,
    }


def run_parallel_cz_xeb_workflow(
    backend: str = "local",
    *,
    chip_characterization: Any = None,
    region_qubits: list[int] | None = None,
    n_qubits: int | None = None,
    patterns: list[list[tuple[int, int]]] | None = None,
    pattern_mode: str = "auto",
    color_idx: int = 0,
    depths: list[int] | None = None,
    instances: int = 20,
    shots: int = 5000,
    noise_model: dict[str, Any] | None = None,
    seed: int | None = 2026,
    cache_dir: str | None = None,
    max_age_hours: float | None = None,
) -> dict[str, Any]:
    """Run parallel-CZ XEB on a chip and return per-pair fidelities.

    Before doing anything this calls
    :func:`uniqc.backend_adapter.preflight.ensure_backend_ready` on
    ``backend``. Missing SDKs, missing or stale chip cache cause an
    immediate, loud error — there are no silent fallbacks.

    A *generic* chip pre-flight calibration: pick (or accept) a region
    of qubits, build parallel CZ patterns, run Haar-U3 + parallel-CZ
    XEB at multiple depths, and fit per-pair ``F(d) = beta · alpha^d``
    on the 2-qubit marginals. Returns a dict whose ``per_pair_results``
    field maps each ``(u, v)`` pair to an :class:`uniqc.XEBResult`
    encoding ``alpha`` (per-cycle CZ fidelity) and its uncertainty.

    Args:
        backend: Backend name (``"local"``, ``"dummy:local:simulator"``,
            ``"dummy:originq:WK_C180"``, ``"originq:WK_C180"``, ...).
        chip_characterization: Required when ``region_qubits``/``patterns``
            need to be derived from the chip topology, or when noise-aware
            simulation is desired (passed to ``DummyAdapter``).
        region_qubits: Explicit list of region qubits. If omitted, derived
            from the chip topology + ``n_qubits`` via ``pick_region``.
        n_qubits: Region size when picking automatically.
        patterns: Explicit list of CZ patterns. If omitted, derived from
            ``pattern_mode``.
        pattern_mode:
            ``"auto"`` — DSatur-color the region's induced edges into
                disjoint matchings (one parallel-XEB run covers all of them).
            ``"three_color"`` — chip-wide 3-coloring of *every* CZ edge,
                use the matching at index ``color_idx`` (one matching).
            ``"single_pair_per_pattern"`` — every pair in the region
                becomes its own one-edge pattern (isolated XEB).
        color_idx: Which color to keep when ``pattern_mode="three_color"``.
        depths: Sweep over circuit depths. Defaults to ``[5, 10, 15, 20, 25, 30]``.
        instances: Random circuit instances per ``(pattern, depth)``.
        shots: Shots per circuit.
        noise_model: Optional explicit DummyAdapter noise model.
        seed: Master corpus RNG seed.
        cache_dir: If set, per-pair :class:`XEBResult` files are saved here.

    Returns:
        Dict with keys:
          * ``region_qubits``: list[int]
          * ``patterns``: list[list[tuple[int,int]]]
          * ``pairs``: list[(u,v)] (every pair touched by any pattern)
          * ``per_pair_fits``: list[PairCircuitFit]
          * ``per_pair_decays``: dict[(u,v), PairDecay]
          * ``per_pair_results``: dict[(u,v), XEBResult]
          * ``corpus_size``: int
    """
    from uniqc.backend_adapter.preflight import ensure_backend_ready
    from uniqc.calibration.xeb.parallel_cz import ParallelCZBenchmarker
    from uniqc.calibration.xeb.topology import (
        ChipTopologyView,
        Region,
        parallel_patterns as _parallel_patterns,
        pick_region,
        three_color_chip,
    )

    # Hard pre-execution gate: missing SDK / chip cache → loud error.
    preflight_chip = ensure_backend_ready(backend, max_age_hours=max_age_hours)
    if chip_characterization is None and preflight_chip is not None:
        chip_characterization = preflight_chip

    if depths is None:
        depths = [5, 10, 15, 20, 25, 30]

    # Derive region + patterns from topology when not explicitly given.
    view: ChipTopologyView | None = None
    if chip_characterization is not None:
        view = ChipTopologyView.from_chip_characterization(chip_characterization)

    if region_qubits is None:
        if view is None:
            raise ValueError(
                "region_qubits or chip_characterization (with n_qubits) is required"
            )
        if n_qubits is None:
            raise ValueError(
                "n_qubits is required when region_qubits is not supplied"
            )
        region = pick_region(view, int(n_qubits), seed=seed or 0)
        region_qs = list(region.qubits)
        region_obj: Region | None = region
    else:
        region_qs = [int(q) for q in region_qubits]
        if view is not None:
            adj = view.adjacency()
            from uniqc.calibration.xeb.topology import _induced_edges
            induced = tuple(_induced_edges(region_qs, adj))
            region_obj = Region(
                qubits=tuple(sorted(region_qs)), edges=induced, score=0.0,
            )
        else:
            region_obj = None

    if patterns is None:
        if pattern_mode == "auto":
            if region_obj is None or not region_obj.edges:
                raise ValueError(
                    "pattern_mode='auto' needs a region with edges; supply "
                    "chip_characterization or explicit patterns"
                )
            patterns = [list(p) for p in _parallel_patterns(region_obj.edges)]
        elif pattern_mode == "three_color":
            if view is None and (region_obj is None or not region_obj.edges):
                raise ValueError(
                    "pattern_mode='three_color' needs chip_characterization "
                    "or a region with edges"
                )
            # Color the region's edges when an explicit region is given,
            # else color the entire chip's coupling map.
            if region_obj is not None and region_obj.edges:
                colors = _parallel_patterns(region_obj.edges, max_K=4)
            else:
                colors = three_color_chip(view, max_K=4)
            if not (0 <= color_idx < len(colors)):
                raise ValueError(
                    f"color_idx={color_idx} out of range; got "
                    f"{len(colors)} colors"
                )
            chosen = list(colors[color_idx])
            patterns = [chosen]
            # Region = qubits actually touched by the chosen matching.
            region_qs = sorted({q for e in chosen for q in e})
        elif pattern_mode == "single_pair_per_pattern":
            if region_obj is None or not region_obj.edges:
                raise ValueError(
                    "pattern_mode='single_pair_per_pattern' needs region edges"
                )
            patterns = [[e] for e in region_obj.edges]
        else:
            raise ValueError(f"unknown pattern_mode={pattern_mode!r}")

    # Build adapter (kept consistent with the rest of this module).
    adapter_kwargs: dict[str, Any] = {}
    if chip_characterization is not None:
        adapter_kwargs["chip_characterization"] = chip_characterization
    if noise_model is not None:
        adapter_kwargs["noise_model"] = noise_model
    adapter = _get_adapter(backend, **adapter_kwargs)

    bench = ParallelCZBenchmarker(
        adapter=adapter, shots=shots, seed=seed, cache_dir=cache_dir,
    )
    result = bench.run(region_qs, patterns, depths, instances=instances)

    return {
        "region_qubits": list(region_qs),
        "patterns": [[tuple(e) for e in p] for p in patterns],
        "pairs": list(result["per_pair_decays"].keys()),
        "per_pair_fits": result["per_pair_fits"],
        "per_pair_decays": result["per_pair_decays"],
        "per_pair_results": result["per_pair_results"],
        "corpus_size": len(result["corpus"]),
    }
