from __future__ import annotations

import pytest


def _sample_chip_info():
    return {
        "mapping": {0: "Q0", 1: "Q1", 2: "Q2"},
        "full_info": {
            "qubits_info": {
                "Q0": {"T1": 21.0, "T2": 31.0},
                "Q1": {"T1": 22.0, "T2": 32.0},
                "Q2": {"T1": 23.0, "T2": 33.0},
            },
            "topological_structure": {
                "Q0_Q1": {"cz": {"fidelity": 0.93}},
                "Q1_Q0": {"cz": {"fidelity": 0.91}},
                "Q1_Q2": {"cz": {"fidelity": 0.84}, "iswap": {"fidelity": 0.82}},
            },
        },
    }


def test_quafu_calibration_extracts_topology_and_conservative_reverse_fidelity():
    from uniqc.backend_adapter.task.adapters.quafu_adapter import (
        _compute_quafu_fidelity,
        _extract_quafu_calibration,
    )

    calibration = _extract_quafu_calibration(
        _sample_chip_info(),
        num_qubits=3,
        valid_gates=["cz", "iswap", "rx"],
    )

    assert [(edge.u, edge.v) for edge in calibration.connectivity] == [(0, 1), (1, 2)]
    assert calibration.available_qubits == (0, 1, 2)
    assert calibration.global_info.two_qubit_gates == ("cz", "iswap")

    edge_gates = {
        (item.qubit_u, item.qubit_v): {gate.gate: gate.fidelity for gate in item.gates}
        for item in calibration.two_qubit_data
    }
    assert edge_gates[(0, 1)]["cz"] == pytest.approx(0.91)
    assert edge_gates[(1, 2)]["cz"] == pytest.approx(0.84)
    assert edge_gates[(1, 2)]["iswap"] == pytest.approx(0.82)

    metrics = _compute_quafu_fidelity(_sample_chip_info())
    assert metrics["avg_2q_fidelity"] == pytest.approx((0.91 + 0.84 + 0.82) / 3)
    assert metrics["coherence_t1"] == pytest.approx(22.0)
    assert metrics["coherence_t2"] == pytest.approx(32.0)


def test_quafu_backend_summary_uses_backend_cache_topology_and_per_edge_details():
    from uniqc.backend_adapter.backend_registry import _normalise_quafu
    from uniqc.backend_adapter.task.adapters.quafu_adapter import _extract_quafu_calibration
    from uniqc.gateway.api.backends import _backend_summary

    calibration = _extract_quafu_calibration(_sample_chip_info(), num_qubits=3)
    raw = [
        {
            "name": "ScQ-Fake",
            "num_qubits": 3,
            "status": "Online",
            "topology": [[edge.u, edge.v] for edge in calibration.connectivity],
            "available_qubits": list(calibration.available_qubits),
            "per_qubit_calibration": [item.to_dict() for item in calibration.single_qubit_data],
            "per_pair_calibration": [item.to_dict() for item in calibration.two_qubit_data],
            "avg_2q_fidelity": 0.5,
        }
    ]

    backend = _normalise_quafu(raw)[0]
    summary = _backend_summary(backend, chip_meta={})

    assert summary["topology"]["has_connectivity"] is True
    assert [node["id"] for node in summary["topology"]["nodes"]] == [0, 1, 2]
    edge_fids = {
        (edge["u"], edge["v"]): edge["fidelity"]
        for edge in summary["topology"]["edges"]
    }
    assert edge_fids[(0, 1)] == pytest.approx(0.91)
    assert edge_fids[(1, 2)] == pytest.approx((0.84 + 0.82) / 2)
    assert len(set(edge_fids.values())) == 2
