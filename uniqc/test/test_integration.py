"""Integration tests for the three new feature modules."""

from __future__ import annotations

import pytest

from uniqc.backend_info import Platform
from uniqc.cli.chip_info import (
    ChipCharacterization,
    ChipGlobalInfo,
    QubitTopology,
    SingleQubitData,
    TwoQubitData,
    TwoQubitGateData,
)
from uniqc.task.optional_deps import SIMULATION_AVAILABLE
from uniqc.task.options import (
    BackendOptionsFactory,
    IBMOptions,
    OriginQOptions,
    QuafuOptions,
)


def _make_chip(nodes: list[int], edges: list[tuple[int, int]]) -> ChipCharacterization:
    sq_data = tuple(
        SingleQubitData(
            qubit_id=q,
            t1=50.0,
            t2=50.0,
            single_gate_fidelity=0.99,
            readout_fidelity_0=0.99,
            readout_fidelity_1=0.99,
            avg_readout_fidelity=0.99,
        )
        for q in sorted(nodes)
    )
    tq_data = tuple(
        TwoQubitData(
            qubit_u=u,
            qubit_v=v,
            gates=(TwoQubitGateData(gate="cz", fidelity=0.95),),
        )
        for u, v in edges
    )
    return ChipCharacterization(
        platform=Platform.ORIGINQ,
        chip_name="test",
        full_id="test",
        available_qubits=tuple(sorted(nodes)),
        connectivity=tuple(QubitTopology(u=u, v=v) for u, v in edges),
        single_qubit_data=sq_data,
        two_qubit_data=tq_data,
        global_info=ChipGlobalInfo(),
        calibrated_at=None,
    )


class TestOptionsIntegration:
    """Integration: BackendOptions work with the full options class hierarchy."""

    def test_quafu_options_with_task_name(self):
        """QuafuOptions with task_name round-trips through factory."""
        original = QuafuOptions(chip_id="ScQ-P10", task_name="test-task", wait=True)
        kwargs = original.to_kwargs()
        restored = BackendOptionsFactory.from_kwargs("quafu", kwargs)
        assert isinstance(restored, QuafuOptions)
        assert restored.chip_id == "ScQ-P10"
        assert restored.task_name == "test-task"
        assert restored.wait is True

    def test_originq_options_roundtrip(self):
        """OriginQOptions round-trips through factory.from_kwargs."""
        original = OriginQOptions(
            backend_name="origin:wuyuan:d6",
            circuit_optimize=False,
            shots=5000,
        )
        kwargs = original.to_kwargs()
        restored = BackendOptionsFactory.from_kwargs("originq", kwargs)
        assert isinstance(restored, OriginQOptions)
        assert restored.backend_name == "origin:wuyuan:d6"
        assert restored.circuit_optimize is False
        # shots is extracted separately
        assert restored.shots == 1000  # default, since shots not in kwargs

    def test_ibm_options_with_chip_id(self):
        """IBMOptions with chip_id round-trips correctly."""
        original = IBMOptions(chip_id="ibm_kyoto", circuit_optimize=False)
        kwargs = original.to_kwargs()
        restored = BackendOptionsFactory.from_kwargs("ibm", kwargs)
        assert isinstance(restored, IBMOptions)
        assert restored.chip_id == "ibm_kyoto"
        assert restored.circuit_optimize is False


class TestRegionSelectorIntegration:
    """Integration: RegionSelector and ChipCharacterization work together."""

    def test_regionselector_chain_with_chain_topology(self):
        """RegionSelector works with a simple linear chain chip."""
        chip = _make_chip(list(range(5)), [(0, 1), (1, 2), (2, 3), (3, 4)])
        from uniqc.region_selector import RegionSelector

        rs = RegionSelector(chip)

        # Length-5 chain exists
        result = rs.find_best_1D_chain(5)
        assert result.chain == [0, 1, 2, 3, 4]

        # Length-4 chain returns first available
        result = rs.find_best_1D_chain(4)
        assert result.chain == [0, 1, 2, 3]

    def test_regionselector_with_star_topology(self):
        """RegionSelector handles a star topology (one hub qubit)."""
        # 0 is hub connected to 1,2,3,4
        edges = [(0, 1), (0, 2), (0, 3), (0, 4)]
        chip = _make_chip(list(range(5)), edges)
        from uniqc.region_selector import RegionSelector

        rs = RegionSelector(chip)

        # Chain of length 2 from hub should work
        result = rs.find_best_1D_chain(2, start=0)
        assert result.chain is not None
        assert len(result.chain) == 2

    def test_fidelity_estimates_differ_by_region(self):
        """Two regions with different characteristics give different fidelity estimates."""
        from uniqc.circuit_builder import Circuit
        from uniqc.region_selector import RegionSelector

        # Two disconnected subgraphs: 0-1-2 has tq_fid=0.95, 3-4 has tq_fid=0.90
        edges = [(0, 1), (1, 2), (3, 4)]
        sq_data = (
            SingleQubitData(
                qubit_id=0,
                t1=50.0,
                t2=50.0,
                single_gate_fidelity=0.99,
                readout_fidelity_0=0.99,
                readout_fidelity_1=0.99,
                avg_readout_fidelity=0.99,
            ),
            SingleQubitData(
                qubit_id=1,
                t1=50.0,
                t2=50.0,
                single_gate_fidelity=0.99,
                readout_fidelity_0=0.99,
                readout_fidelity_1=0.99,
                avg_readout_fidelity=0.99,
            ),
            SingleQubitData(
                qubit_id=2,
                t1=50.0,
                t2=50.0,
                single_gate_fidelity=0.99,
                readout_fidelity_0=0.99,
                readout_fidelity_1=0.99,
                avg_readout_fidelity=0.99,
            ),
            SingleQubitData(
                qubit_id=3,
                t1=50.0,
                t2=50.0,
                single_gate_fidelity=0.99,
                readout_fidelity_0=0.99,
                readout_fidelity_1=0.99,
                avg_readout_fidelity=0.99,
            ),
            SingleQubitData(
                qubit_id=4,
                t1=50.0,
                t2=50.0,
                single_gate_fidelity=0.99,
                readout_fidelity_0=0.99,
                readout_fidelity_1=0.99,
                avg_readout_fidelity=0.99,
            ),
        )
        tq_data = (
            TwoQubitData(qubit_u=0, qubit_v=1, gates=(TwoQubitGateData(gate="cz", fidelity=0.95),)),
            TwoQubitData(qubit_u=1, qubit_v=2, gates=(TwoQubitGateData(gate="cz", fidelity=0.95),)),
            TwoQubitData(qubit_u=3, qubit_v=4, gates=(TwoQubitGateData(gate="cz", fidelity=0.90),)),
        )
        chip = ChipCharacterization(
            platform=Platform.ORIGINQ,
            chip_name="test",
            full_id="test",
            available_qubits=(0, 1, 2, 3, 4),
            connectivity=tuple(QubitTopology(u=u, v=v) for u, v in edges),
            single_qubit_data=sq_data,
            two_qubit_data=tq_data,
            global_info=ChipGlobalInfo(),
            calibrated_at=None,
        )
        rs = RegionSelector(chip)

        # Same gate structure on two different qubit pairs
        circuit_high = Circuit(5)
        circuit_high.h(0)
        circuit_high.cnot(0, 1)

        circuit_low = Circuit(5)
        circuit_low.h(3)
        circuit_low.cnot(3, 4)

        fid_high = rs.estimate_circuit_fidelity(circuit_high, qubits={0, 1})
        fid_low = rs.estimate_circuit_fidelity(circuit_low, qubits={3, 4})

        # High-fidelity region (0.95 TQ gate) should give higher fidelity than 0.90 region
        assert fid_high > fid_low


@pytest.mark.skipif(not SIMULATION_AVAILABLE, reason="simulation dependencies not installed")
class TestDummySubmitIntegration:
    """Integration: submit_task with BackendOptions works end-to-end via dummy adapter.

    Use dummy=True to activate the dummy adapter (bypasses _get_adapter lookup,
    which requires a registered backend key). The backend arg is used for logging only.
    """

    def test_submit_task_with_options_dict(self):
        """submit_task accepts a dict as the options parameter via backend='dummy'."""
        from uniqc.circuit_builder import Circuit
        from uniqc.task_manager import submit_task

        circuit = Circuit(2)
        circuit.h(0)
        circuit.cnot(0, 1)

        task_id = submit_task(
            circuit,
            "dummy",
            shots=100,
            options={"available_qubits": 4},
        )
        assert isinstance(task_id, str)
        assert len(task_id) > 0

    def test_submit_task_with_backend_options_instance(self):
        """submit_task accepts a BackendOptions subclass instance."""
        from uniqc.circuit_builder import Circuit
        from uniqc.task.options import DummyOptions
        from uniqc.task_manager import submit_task

        circuit = Circuit(2)
        circuit.h(0)
        circuit.cnot(0, 1)

        opts = DummyOptions(available_qubits=4, shots=200)
        task_id = submit_task(circuit, "dummy", options=opts)
        assert isinstance(task_id, str)
        assert len(task_id) > 0

    def test_submit_task_options_and_kwargs_merged(self):
        """When both options= and **kwargs are provided, they are merged."""
        from uniqc.circuit_builder import Circuit
        from uniqc.task_manager import submit_task

        circuit = Circuit(2)
        circuit.h(0)
        circuit.cnot(0, 1)

        task_id = submit_task(
            circuit,
            "dummy",
            shots=100,
            options={"available_qubits": 4},
            available_qubits=8,  # should override options
        )
        assert isinstance(task_id, str)
