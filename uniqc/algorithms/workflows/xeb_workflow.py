"""High-level XEB workflow combining calibration, readout EM, and fidelity fitting.

Chip-agnostic: works with any backend supported by UnifiedQuantum.
For WK180-specific usage, see ``examples/wk180/xeb.py``.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "run_1q_xeb_workflow",
    "run_2q_xeb_workflow",
    "run_parallel_xeb_workflow",
]


def _get_adapter(backend: str, **kwargs) -> Any:
    """Get a QuantumAdapter for the given backend name.

    Args:
        backend: Backend identifier, e.g. "dummy", "originq:PQPUMESH8".
            For OriginQ backends the chip name (after "originq:") is extracted
            and passed as ``backend_name`` to ``OriginQAdapter``.
    """
    from uniqc.backend_adapter.task.adapters import (
        DummyAdapter,
        OriginQAdapter,
        QuafuAdapter,
    )

    if backend == "dummy" or backend.startswith("dummy:"):
        from uniqc.backend_adapter.dummy_backend import dummy_adapter_kwargs

        return DummyAdapter(**dummy_adapter_kwargs(backend, **kwargs))
    elif backend.startswith("origin"):
        # Extract chip name: "originq:PQPUMESH8" → "PQPUMESH8"
        chip = backend.split(":", 1)[1] if ":" in backend else backend
        return OriginQAdapter(backend_name=chip)
    elif backend.startswith("quafu"):
        return QuafuAdapter(**kwargs)
    else:
        # Fall back to dummy for unknown backends
        return DummyAdapter(**kwargs)


def run_1q_xeb_workflow(
    backend: str = "dummy",
    qubits: list[int] | None = None,
    depths: list[int] | None = None,
    n_circuits: int = 50,
    shots: int = 1000,
    use_readout_em: bool = True,
    max_age_hours: float = 24.0,
    chip_characterization: Any = None,
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
        seed: Random seed for circuit generation.

    Returns:
        Dict mapping qubit index → XEBResult.
    """
    from uniqc.calibration.xeb.benchmarker import XEBenchmarker
    from uniqc.calibration.readout import ReadoutCalibrator
    from uniqc.qem import ReadoutEM

    if depths is None:
        depths = [5, 10, 20, 50, 100]
    if qubits is None:
        qubits = [0, 1, 2]

    adapter_kwargs: dict[str, Any] = {}
    if chip_characterization is not None:
        adapter_kwargs["chip_characterization"] = chip_characterization

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
    backend: str = "dummy",
    pairs: list[tuple[int, int]] | None = None,
    depths: list[int] | None = None,
    n_circuits: int = 50,
    shots: int = 1000,
    use_readout_em: bool = True,
    max_age_hours: float = 24.0,
    chip_characterization: Any = None,
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
        seed: Random seed.
        entangler_gates: Per-pair 2-qubit gate name override.

    Returns:
        Dict mapping (u, v) → XEBResult.
    """
    from uniqc.calibration.xeb.benchmarker import XEBenchmarker
    from uniqc.calibration.readout import ReadoutCalibrator
    from uniqc.qem import ReadoutEM

    if depths is None:
        depths = [5, 10, 20, 50]
    if pairs is None:
        pairs = [(0, 1), (1, 2)]

    adapter_kwargs: dict[str, Any] = {}
    if chip_characterization is not None:
        adapter_kwargs["chip_characterization"] = chip_characterization

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
    backend: str = "dummy",
    chip_characterization: Any = None,
    depths: list[int] | None = None,
    n_circuits: int = 50,
    shots: int = 1000,
    use_readout_em: bool = True,
    max_age_hours: float = 24.0,
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
        seed: Random seed.
        target_qubits: Optional subset of qubits to include (uses full topology if None).

    Returns:
        Dict with keys: ``patterns`` (ParallelPatternResult),
        ``results`` (per-pair XEBResult), ``pairs``.
    """
    from uniqc.calibration.xeb.benchmarker import XEBenchmarker
    from uniqc.calibration.readout import ReadoutCalibrator
    from uniqc.calibration.xeb.patterns import ParallelPatternGenerator
    from uniqc.qem import ReadoutEM

    if chip_characterization is None:
        raise ValueError("chip_characterization is required for parallel XEB")

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
        raise ValueError("No edges found in chip topology")

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
