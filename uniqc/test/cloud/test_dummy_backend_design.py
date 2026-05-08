"""Tests for canonical dummy backend identifiers."""

from __future__ import annotations

import pytest


def test_resolve_unconstrained_dummy():
    from uniqc.backend_adapter.dummy_backend import resolve_dummy_backend

    spec = resolve_dummy_backend("dummy", allow_fetch=False)

    assert spec.identifier == "dummy"
    assert spec.available_qubits is None
    assert spec.available_topology is None
    assert spec.noise_source == "none"


def test_resolve_virtual_line_topology():
    from uniqc.backend_adapter.dummy_backend import resolve_dummy_backend

    spec = resolve_dummy_backend("dummy:virtual-line-3", allow_fetch=False)

    assert spec.identifier == "dummy:virtual-line-3"
    assert spec.available_qubits == [0, 1, 2]
    assert spec.available_topology == [[0, 1], [1, 2]]
    assert spec.noise_source == "none"


def test_resolve_virtual_grid_topology():
    from uniqc.backend_adapter.dummy_backend import resolve_dummy_backend

    spec = resolve_dummy_backend("dummy:virtual-grid-2x2", allow_fetch=False)

    assert spec.identifier == "dummy:virtual-grid-2x2"
    assert spec.available_qubits == [0, 1, 2, 3]
    assert sorted(spec.available_topology) == [[0, 1], [0, 2], [1, 3], [2, 3]]


def test_resolve_chip_backed_dummy_with_explicit_characterization():
    from uniqc.backend_adapter.backend_info import Platform, QubitTopology
    from uniqc.backend_adapter.dummy_backend import resolve_dummy_backend
    from uniqc.cli.chip_info import ChipCharacterization, SingleQubitData

    chip = ChipCharacterization(
        platform=Platform.ORIGINQ,
        chip_name="WK_C180",
        full_id="originq:WK_C180",
        available_qubits=(0, 1),
        connectivity=(QubitTopology(0, 1),),
        single_qubit_data=(SingleQubitData(0, single_gate_fidelity=0.99),),
    )

    spec = resolve_dummy_backend(
        "dummy:originq:wk-c180",
        allow_fetch=False,
        chip_characterization=chip,
    )

    assert spec.identifier == "dummy:originq:WK_C180"
    assert spec.source_platform == Platform.ORIGINQ
    assert spec.source_name == "WK_C180"
    assert spec.chip_characterization is chip
    assert spec.noise_source == "chip_characterization"


def test_builtin_dummy_backend_infos_include_virtual_fixtures():
    from uniqc.backend_adapter.dummy_backend import list_dummy_backend_infos

    ids = {b.full_id() for b in list_dummy_backend_infos()}

    assert "dummy" in ids
    assert "dummy:virtual-line-3" in ids
    assert "dummy:virtual-grid-2x2" in ids
    assert all(not backend_id.startswith("dummy:originq:") for backend_id in ids)


@pytest.mark.requires_cpp
def test_dummy_task_id_includes_backend_identity():
    from uniqc.backend_adapter.task.adapters.dummy_adapter import DummyAdapter

    circuit = "QINIT 2\nCREG 2\nH q[0]\nCNOT q[0],q[1]\nMEASURE q[0], c[0]"

    ideal = DummyAdapter(backend_id="dummy")
    line = DummyAdapter(
        backend_id="dummy:virtual-line-3",
        available_qubits=[0, 1, 2],
        available_topology=[[0, 1], [1, 2]],
    )

    assert ideal.submit(circuit, shots=10) != line.submit(circuit, shots=10)


@pytest.mark.requires_cpp
def test_dummy_dry_run_enforces_virtual_backend_constraints():
    from uniqc.backend_adapter.task.adapters.dummy_adapter import DummyAdapter

    circuit = "QINIT 4\nCREG 4\nH q[0]\nCNOT q[0], q[3]\nMEASURE q[0], c[0]"
    line = DummyAdapter(
        backend_id="dummy:virtual-line-3",
        available_qubits=[0, 1, 2],
        available_topology=[[0, 1], [1, 2]],
    )

    result = line.dry_run(circuit, shots=10)

    assert result.success is False
    assert result.backend_name == "dummy:virtual-line-3"
    assert "Available qubits" in (result.error or "")


# --- Regression tests for chip-backed dummy relayout (NEW-U1/NEW-U2 hotfix) ---

def _wk_c180_backed_dummy_spec():
    """Build a chip-backed dummy spec mirroring the user-reported case."""
    from uniqc.backend_adapter.backend_info import Platform, QubitTopology
    from uniqc.backend_adapter.dummy_backend import resolve_dummy_backend
    from uniqc.cli.chip_info import (
        ChipCharacterization,
        SingleQubitData,
        TwoQubitData,
        TwoQubitGateData,
    )

    # Minimal characterization: chip excludes q[13] (bad) and exposes
    # safe linear chain {58,68,77,86} plus a separate (0-1) edge.
    safe = [58, 68, 77, 86]
    edges = [(58, 68), (68, 77), (77, 86), (0, 1)]
    chip = ChipCharacterization(
        platform=Platform.ORIGINQ,
        chip_name="WK_C180",
        full_id="originq:WK_C180",
        available_qubits=tuple(safe + [0, 1]),
        connectivity=tuple(QubitTopology(a, b) for a, b in edges),
        single_qubit_data=tuple(
            SingleQubitData(q, single_gate_fidelity=0.999) for q in safe + [0, 1]
        ),
        two_qubit_data=tuple(
            TwoQubitData(a, b, gates=(TwoQubitGateData(gate="cz", fidelity=0.99),))
            for a, b in edges
        ),
    )
    return resolve_dummy_backend(
        "dummy:originq:WK_C180",
        chip_characterization=chip,
        allow_fetch=False,
    )


def test_chip_backed_dummy_local_compile_zero_preserves_user_qubits():
    """local_compile=0 must NOT relayout the user's chosen physical qubits."""
    from uniqc.backend_adapter.task_manager import _compile_for_chip_backed_dummy
    from uniqc.circuit_builder import Circuit

    spec = _wk_c180_backed_dummy_spec()
    c = Circuit(); c.h(58); c.cz(58, 68); c.measure(58); c.measure(68)

    ir, _ = _compile_for_chip_backed_dummy(c, spec, None, local_compile=0)
    assert "q[58]" in ir and "q[68]" in ir
    assert "q[13]" not in ir and "q[21]" not in ir


def test_chip_backed_dummy_available_qubits_blocks_bad_relayout():
    """available_qubits must keep the relayout off the chip's bad qubits.

    Even with local_compile>0, the layout pass must respect the user-provided
    allow-list and never silently land on an excluded qubit (q[13] here).
    """
    from uniqc.backend_adapter.task_manager import _compile_for_chip_backed_dummy
    from uniqc.circuit_builder import Circuit

    spec = _wk_c180_backed_dummy_spec()
    c = Circuit(); c.h(58); c.cz(58, 68); c.measure(58); c.measure(68)

    ir, _ = _compile_for_chip_backed_dummy(
        c, spec, None,
        local_compile=2,
        available_qubits=[58, 68, 77, 86],
    )
    assert "q[13]" not in ir and "q[21]" not in ir
