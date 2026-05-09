"""Tests for per-pair marginal F_XEB analysis."""

from __future__ import annotations

import collections

import numpy as np
import pytest

from uniqc.calibration.xeb.parallel_cz import (
    Schedule,
    build_parallel_cz_xeb_corpus,
    fit_pair_decays,
    pair_ideal_probs,
    pair_marginal_counts,
    per_pair_F_XEB,
)


def test_pair_marginal_counts_lsb_convention():
    """Bit `k` (LSB+k) of the integer index = state of k-th measured qubit."""
    # q0 in |1>, q1=q2=q3=|0>; integer index = 1 ('0001' formatted MSB-first)
    counts = {format(1, "04b"): 5000}
    measured = [0, 1, 2, 3]
    # Pair (0,1): q0=1, q1=0 -> idx = (q1 << 1) | q0 = 1
    mc = pair_marginal_counts(counts, measured, (0, 1))
    assert mc == {1: 5000}
    # Reversing the pair swaps bit positions.
    mc_rev = pair_marginal_counts(counts, measured, (1, 0))
    assert mc_rev == {2: 5000}
    # Pair on idle qubits (2, 3) -> both 0
    mc_idle = pair_marginal_counts(counts, measured, (2, 3))
    assert mc_idle == {0: 5000}


def test_pair_marginal_counts_handles_int_keys():
    counts = {1: 1000, 5: 200}
    mc = pair_marginal_counts(counts, [0, 1, 2, 3], (0, 2))
    # idx=1: q0=1, q2=0 -> (0<<1)|1 = 1
    # idx=5 = 0b0101: q0=1, q2=1 -> (1<<1)|1 = 3
    assert mc == {1: 1000, 3: 200}


def test_pair_ideal_probs_matches_full_simulation_for_disjoint_pairs():
    """For a circuit with disjoint CZ pairs, the 2-qubit subcircuit
    distribution must equal the marginal of the full distribution."""
    from uniqc.simulator import OriginIR_Simulator

    region = (0, 1, 2, 3)
    pattern = ((0, 1), (2, 3))
    rng = np.random.default_rng(42)
    cycles = []
    for _ in range(3):
        angles = tuple(
            (
                float(rng.uniform(0, np.pi)),
                float(rng.uniform(0, 2 * np.pi)),
                float(rng.uniform(0, 2 * np.pi)),
            )
            for _ in region
        )
        cycles.append((angles, pattern))
    sched = Schedule(
        region_qubits=region, measured_qubits=region,
        cycles=tuple(cycles), seed=0,
    )

    # Build the 4-qubit reference circuit and marginalise via numpy.
    from uniqc import Circuit
    c = Circuit()
    for angles, pat in sched.cycles:
        for q, (t, p, l) in zip(region, angles):
            c.u3(q, t, p, l)
        for a, b in pat:
            c.cz(a, b)
    for q in region:
        c.measure(q)
    sim = OriginIR_Simulator(backend_type="statevector")
    full_probs = np.asarray(sim.simulate_pmeasure(c.originir), dtype=float)

    # Marginal on (0,1): sum over q2, q3 (bits 2 and 3). idx = (q1<<1)|q0.
    marg = np.zeros(4)
    for idx in range(16):
        q0 = (idx >> 0) & 1
        q1 = (idx >> 1) & 1
        marg[(q1 << 1) | q0] += full_probs[idx]

    sub = pair_ideal_probs(sched, (0, 1))
    np.testing.assert_allclose(sub, marg, atol=1e-9)


def test_per_pair_F_XEB_noiseless_close_to_one_at_low_depth():
    """At depth 1, a single Haar layer + CZ has F_XEB = D <P_id^2>_meas - 1
    averaged over Haar-random circuits ≈ (D-1)/(D+1) ≈ 0.6 for D=4. With
    perfect simulation and many shots, the fit should give alpha close to 1."""
    from uniqc.simulator import OriginIR_Simulator

    region = [0, 1]
    patterns = [[(0, 1)]]
    depths = [1, 2, 3, 4]
    instances = 12
    corpus = build_parallel_cz_xeb_corpus(
        region, patterns, depths, instances, seed=2026,
    )
    sim = OriginIR_Simulator(backend_type="statevector")
    rng = np.random.default_rng(0)
    records = []
    for pc in corpus:
        probs = np.asarray(sim.simulate_pmeasure(pc.circuit.originir), dtype=float)
        probs = probs / probs.sum()
        samples = rng.choice(len(probs), size=20000, p=probs)
        keys, vals = np.unique(samples, return_counts=True)
        counts = {format(int(k), "02b"): int(v) for k, v in zip(keys, vals)}
        records.append({
            "record_id": pc.record_id,
            "schedule": pc.schedule,
            "pattern_idx": pc.pattern_idx,
            "pattern": pc.pattern,
            "depth": pc.depth,
            "instance": pc.instance,
            "counts": counts,
        })

    fits = per_pair_F_XEB(records, [(0, 1)])
    assert len(fits) == len(corpus)
    decays = fit_pair_decays(fits)
    assert (0, 1) in decays
    # Noiseless => alpha very close to 1.0
    assert decays[(0, 1)].alpha == pytest.approx(1.0, abs=0.05)


def test_per_pair_F_XEB_detects_depolarising_decay():
    """Manually inject a depolarising channel (mix ideal with uniform) and
    verify the fitted alpha matches the depolarising survival rate."""
    from uniqc.simulator import OriginIR_Simulator

    region = [0, 1]
    patterns = [[(0, 1)]]
    depths = [1, 2, 4, 6, 8]
    instances = 16
    corpus = build_parallel_cz_xeb_corpus(
        region, patterns, depths, instances, seed=11,
    )
    sim = OriginIR_Simulator(backend_type="statevector")
    rng = np.random.default_rng(0)
    p_per_cycle = 0.9  # survival rate per cycle
    records = []
    for pc in corpus:
        probs = np.asarray(sim.simulate_pmeasure(pc.circuit.originir), dtype=float)
        probs = probs / probs.sum()
        D = len(probs)
        # Apply a depth-dependent depolarising channel: F_d = p^d.
        F_d = p_per_cycle ** pc.depth
        noisy = F_d * probs + (1 - F_d) / D
        samples = rng.choice(len(noisy), size=20000, p=noisy)
        keys, vals = np.unique(samples, return_counts=True)
        counts = {format(int(k), "02b"): int(v) for k, v in zip(keys, vals)}
        records.append({
            "record_id": pc.record_id,
            "schedule": pc.schedule,
            "pattern_idx": pc.pattern_idx,
            "pattern": pc.pattern,
            "depth": pc.depth,
            "instance": pc.instance,
            "counts": counts,
        })

    fits = per_pair_F_XEB(records, [(0, 1)])
    decays = fit_pair_decays(fits)
    assert (0, 1) in decays
    assert decays[(0, 1)].alpha == pytest.approx(p_per_cycle, abs=0.03)


def test_per_pair_F_XEB_skips_pairs_outside_measured():
    """If a pair's qubits are not in the schedule's measured_qubits, skip it."""
    region = [0, 1, 2]
    patterns = [[(0, 1)]]
    depths = [2]
    instances = 1
    corpus = build_parallel_cz_xeb_corpus(region, patterns, depths, instances, seed=0)
    pc = corpus[0]
    counts = {format(0, "03b"): 1000}
    record = {
        "record_id": pc.record_id, "schedule": pc.schedule,
        "pattern_idx": pc.pattern_idx, "pattern": pc.pattern,
        "depth": pc.depth, "instance": pc.instance, "counts": counts,
    }
    fits = per_pair_F_XEB([record], [(0, 1), (5, 6)])
    pairs_seen = {f.pair for f in fits}
    assert pairs_seen == {(0, 1)}
