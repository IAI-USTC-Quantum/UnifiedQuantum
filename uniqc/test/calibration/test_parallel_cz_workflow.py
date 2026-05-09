"""End-to-end test for ParallelCZBenchmarker / parallel-CZ XEB workflow."""

from __future__ import annotations

import pytest

from uniqc.calibration.xeb import ParallelCZBenchmarker, parallel_patterns


def _dummy_adapter(noise=None):
    from uniqc.backend_adapter.task.adapters import DummyAdapter
    if noise is None:
        return DummyAdapter()
    return DummyAdapter(noise_model=noise)


def test_benchmarker_noiseless_returns_alpha_near_one(tmp_path):
    adapter = _dummy_adapter()
    bench = ParallelCZBenchmarker(
        adapter=adapter, shots=4000, seed=2026, cache_dir=str(tmp_path),
    )
    result = bench.run(
        region_qubits=[0, 1, 2, 3],
        patterns=[[(0, 1), (2, 3)]],
        depths=[2, 4, 6, 8],
        instances=8,
    )
    decays = result["per_pair_decays"]
    assert {(0, 1), (2, 3)} <= set(decays.keys())
    for pair, dec in decays.items():
        assert dec.alpha == pytest.approx(1.0, abs=0.06), (
            f"pair {pair}: expected noiseless alpha≈1, got {dec.alpha}"
        )
    # Per-pair XEBResult cached + returned.
    assert {(0, 1), (2, 3)} <= set(result["per_pair_results"].keys())
    cached = list(tmp_path.glob("xeb_2q_parallel_*.json"))
    assert len(cached) == len(result["per_pair_results"])


def test_benchmarker_noisy_alpha_below_one():
    """A modest depolarising error per CZ should pull alpha clearly below 1."""
    adapter = _dummy_adapter(noise={"depol": 0.1, "readout": 0.0})
    bench = ParallelCZBenchmarker(
        adapter=adapter, shots=4000, seed=2026,
    )
    result = bench.run(
        region_qubits=[0, 1, 2, 3],
        patterns=[[(0, 1), (2, 3)]],
        depths=[2, 4, 6, 8],
        instances=8,
    )
    decays = result["per_pair_decays"]
    assert (0, 1) in decays and (2, 3) in decays
    for dec in decays.values():
        assert dec.alpha < 0.99


def test_workflow_with_explicit_region_and_patterns():
    from uniqc.algorithms.workflows.xeb_workflow import run_parallel_cz_xeb_workflow

    out = run_parallel_cz_xeb_workflow(
        backend="dummy:local:simulator",
        region_qubits=[0, 1, 2, 3],
        patterns=[[(0, 1), (2, 3)]],
        depths=[2, 4, 6],
        instances=6,
        shots=4000,
        seed=2026,
    )
    assert set(out["pairs"]) == {(0, 1), (2, 3)}
    for pair in out["pairs"]:
        assert pair in out["per_pair_decays"]
        assert out["per_pair_decays"][pair].alpha == pytest.approx(1.0, abs=0.06)


def test_workflow_auto_pattern_mode_from_region():
    """pattern_mode='auto' colors the region's induced edges. With an
    explicit region but no chip_characterization, this needs at least
    enough info to infer edges — test the explicit-patterns path stays
    available, and that the all-or-nothing argument validation triggers."""
    from uniqc.algorithms.workflows.xeb_workflow import run_parallel_cz_xeb_workflow

    with pytest.raises(ValueError):
        # Auto mode without chip topology = no edges to color
        run_parallel_cz_xeb_workflow(
            backend="dummy:local:simulator",
            region_qubits=[0, 1, 2, 3],
            pattern_mode="auto",
            depths=[2],
            instances=1,
            shots=200,
        )


def test_parallel_patterns_colors_region_edges():
    """Sanity check: parallel_patterns on a small region returns
    the right number of patterns to cover all edges with no overlap."""
    edges = [(0, 1), (1, 2), (2, 3)]
    patterns = parallel_patterns(edges)
    flat = [e for pat in patterns for e in pat]
    assert sorted({(min(a, b), max(a, b)) for a, b in flat}) == sorted(edges)
    for pat in patterns:
        qs = set()
        for a, b in pat:
            assert a not in qs and b not in qs
            qs.update((a, b))
