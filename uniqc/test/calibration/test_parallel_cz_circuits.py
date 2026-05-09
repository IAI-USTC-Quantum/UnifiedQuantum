"""Tests for parallel-CZ XEB circuit + corpus builder."""

from __future__ import annotations

import re

import pytest

from uniqc.calibration.xeb.parallel_cz import (
    ProbeCircuit,
    Schedule,
    build_parallel_cz_xeb_circuit,
    build_parallel_cz_xeb_corpus,
)


def test_single_circuit_shape():
    pc = build_parallel_cz_xeb_circuit(
        [0, 1, 2, 3], [(0, 1), (2, 3)], depth=3, seed=0, instance=0,
    )
    assert isinstance(pc, ProbeCircuit)
    assert isinstance(pc.schedule, Schedule)
    assert pc.depth == 3
    assert pc.schedule.depth == 3
    assert pc.schedule.region_qubits == (0, 1, 2, 3)
    assert pc.schedule.measured_qubits == (0, 1, 2, 3)
    # Each cycle has angles for every region qubit and the same pattern.
    for angles, pat in pc.schedule.cycles:
        assert len(angles) == 4
        assert pat == ((0, 1), (2, 3))


def test_only_u3_cz_measure_in_originir():
    pc = build_parallel_cz_xeb_circuit(
        [0, 1, 2, 3], [(0, 1), (2, 3)], depth=4, seed=0,
    )
    ir = pc.circuit.originir
    gate_lines = [
        ln.strip() for ln in ir.splitlines()
        if ln.strip()
        and not ln.startswith("QINIT")
        and not ln.startswith("CREG")
    ]
    allowed = re.compile(r"^(U3|CZ|MEASURE)\b")
    for ln in gate_lines:
        assert allowed.match(ln), f"unexpected gate line: {ln!r}"


def test_gate_counts_match_depth():
    region = [0, 1, 2, 3]
    pat = [(0, 1), (2, 3)]
    pc = build_parallel_cz_xeb_circuit(region, pat, depth=5, seed=42)
    ir = pc.circuit.originir
    n_u3 = sum(1 for ln in ir.splitlines() if ln.startswith("U3"))
    n_cz = sum(1 for ln in ir.splitlines() if ln.startswith("CZ"))
    n_meas = sum(1 for ln in ir.splitlines() if ln.startswith("MEASURE"))
    # depth=5 cycles, 4 U3 per cycle, 2 CZ per cycle, 4 measures.
    assert n_u3 == 5 * 4
    assert n_cz == 5 * 2
    assert n_meas == 4


def test_seed_determinism():
    pc1 = build_parallel_cz_xeb_circuit(
        [0, 1, 2], [(0, 1)], depth=4, seed=7, instance=3,
    )
    pc2 = build_parallel_cz_xeb_circuit(
        [0, 1, 2], [(0, 1)], depth=4, seed=7, instance=3,
    )
    assert pc1.circuit.originir == pc2.circuit.originir
    assert pc1.schedule.cycles == pc2.schedule.cycles


def test_different_instances_differ():
    pc1 = build_parallel_cz_xeb_circuit(
        [0, 1, 2], [(0, 1)], depth=4, seed=7, instance=0,
    )
    pc2 = build_parallel_cz_xeb_circuit(
        [0, 1, 2], [(0, 1)], depth=4, seed=7, instance=1,
    )
    assert pc1.circuit.originir != pc2.circuit.originir


def test_pattern_outside_region_rejected():
    with pytest.raises(ValueError, match="outside region"):
        build_parallel_cz_xeb_circuit([0, 1], [(0, 5)], depth=2)


def test_corpus_shape_and_unique_record_ids():
    patterns = [[(0, 1)], [(2, 3)]]
    depths = [2, 4, 8]
    instances = 5
    corpus = build_parallel_cz_xeb_corpus(
        [0, 1, 2, 3], patterns, depths, instances, seed=0,
    )
    assert len(corpus) == len(patterns) * len(depths) * instances
    rids = [pc.record_id for pc in corpus]
    assert len(set(rids)) == len(rids)
    # pattern_idx + depth + instance reachable from record_id.
    for pc in corpus:
        assert pc.record_id == f"P{pc.pattern_idx}_d{pc.depth}_inst{pc.instance}"
