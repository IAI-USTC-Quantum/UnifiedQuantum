"""Regression test for the tiny-circuit-on-large-chip router KeyError.

Previously, ``_route_with_fidelity`` could raise ``KeyError`` when a tiny
2-qubit circuit was routed onto a large (~180-qubit) chip where most
qubits/edges had no calibration data. The failure originated in
``_estimate_circuit_fidelity_from_lines`` when it looked up either:

* a logical qubit that wasn't included in ``l2p`` (because the dict was
  truncated to ``min(n_qubits, len(initial_layout))``), or
* a chip qubit / edge that had no calibration entry.

The fix pads ``l2p`` with identity fallbacks and the lookup site uses
``.get(..., _DEFAULT_FIDELITY)`` with sorted edge tuples.
"""

from __future__ import annotations

import pytest

from uniqc.backend_adapter.backend_info import Platform, QubitTopology
from uniqc.cli.chip_info import (
    ChipCharacterization,
    ChipGlobalInfo,
    SingleQubitData,
    TwoQubitData,
    TwoQubitGateData,
)
from uniqc.compile.compiler import _route_with_fidelity

_N_QUBITS = 180


def _build_linear_topology(n_qubits: int) -> list[tuple[int, int]]:
    """Linear chain ``0-1-2-...-n_qubits-1`` as an undirected list of edges."""
    edges: list[tuple[int, int]] = []
    for i in range(n_qubits - 1):
        edges.append((i, i + 1))
        edges.append((i + 1, i))  # store both directions like a real chip
    return edges


def _build_large_sparse_chip() -> tuple[ChipCharacterization, list[tuple[int, int]]]:
    """A 180-qubit linear chip with calibration data on only a few qubits.

    The vast majority of single-qubit and two-qubit entries are missing —
    exactly the conditions that triggered the KeyError.
    """
    topology_pairs = _build_linear_topology(_N_QUBITS)
    connectivity = tuple(QubitTopology(u=u, v=v) for u, v in topology_pairs)

    # Only calibrate 5 qubits out of 180 (rest will have no SQ fidelity).
    calibrated_sq = {3: 0.999, 5: 0.998, 7: 0.997, 50: 0.995, 100: 0.990}
    single_qubit_data = tuple(SingleQubitData(qubit_id=q, single_gate_fidelity=f) for q, f in calibrated_sq.items())

    # Only calibrate a couple of edges out of ~179.
    calibrated_edges = [
        (3, 4, 0.985),
        (5, 6, 0.980),
        (50, 51, 0.975),
    ]
    two_qubit_data = tuple(
        TwoQubitData(
            qubit_u=u,
            qubit_v=v,
            gates=(TwoQubitGateData(gate="cz", fidelity=f),),
        )
        for u, v, f in calibrated_edges
    )

    chip = ChipCharacterization(
        platform=Platform.DUMMY,
        chip_name="LARGE_SPARSE_180",
        full_id="dummy:LARGE_SPARSE_180",
        available_qubits=tuple(range(_N_QUBITS)),
        connectivity=connectivity,
        single_qubit_data=single_qubit_data,
        two_qubit_data=two_qubit_data,
        global_info=ChipGlobalInfo(
            single_qubit_gates=("h", "x", "sx"),
            two_qubit_gates=("cz",),
        ),
    )

    # Undirected edge list passed to _route_with_fidelity (caller form).
    topology_for_router = [(u, v) for (u, v) in topology_pairs]
    return chip, topology_for_router


def test_route_with_fidelity_tiny_bell_on_large_sparse_chip():
    """Bell-pair OriginIR on a 180-qubit sparse chip must not raise KeyError."""
    chip, topology = _build_large_sparse_chip()
    assert len(topology) > 100, "regression scenario requires a 'large' chip"

    bell_originir = "QINIT 2\nH q[0]\nCNOT q[0], q[1]\n"

    # Must not raise (previously: KeyError in _route_with_fidelity).
    routed_ir, swap_count, fidelity, initial_layout = _route_with_fidelity(bell_originir, topology, chip)

    assert routed_ir == bell_originir, "router should not rewrite OriginIR"
    assert swap_count == 0, "this layer never inserts SWAPs"
    assert 0.0 < fidelity <= 1.0, f"fidelity must be in (0, 1], got {fidelity}"

    if initial_layout is not None:
        assert len(initial_layout) == 2
        chip_qubits = {u for edge in topology for u in edge}
        for q in initial_layout:
            assert q in chip_qubits, f"physical qubit {q} not in chip topology"


@pytest.mark.parametrize(
    "originir",
    [
        "QINIT 1\nH q[0]\n",
        "QINIT 2\nH q[0]\nCNOT q[0], q[1]\n",
        "QINIT 2\nH q[0]\nCNOT q[1], q[0]\n",  # reversed edge ordering
    ],
)
def test_route_with_fidelity_tiny_circuits_no_keyerror(originir):
    """Single-qubit and reversed-edge two-qubit circuits also stay safe."""
    chip, topology = _build_large_sparse_chip()
    routed_ir, swap_count, fidelity, _layout = _route_with_fidelity(originir, topology, chip)
    assert routed_ir == originir
    assert swap_count == 0
    assert 0.0 < fidelity <= 1.0
