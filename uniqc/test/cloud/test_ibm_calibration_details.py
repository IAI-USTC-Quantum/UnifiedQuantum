from __future__ import annotations

import pytest


class _InstructionProps:
    def __init__(self, *, error: float | None = None, duration: float | None = None) -> None:
        self.error = error
        self.duration = duration


class _Target:
    operation_names = ["sx", "cz", "measure"]

    def __init__(self) -> None:
        self._ops = {
            "sx": {
                (0,): _InstructionProps(error=0.001, duration=30e-9),
                (1,): _InstructionProps(error=0.002, duration=31e-9),
                (2,): _InstructionProps(error=0.003, duration=32e-9),
            },
            "cz": {
                (0, 1): _InstructionProps(error=0.041, duration=68e-9),
                (1, 2): _InstructionProps(error=0.083, duration=72e-9),
            },
            "measure": {
                (0,): _InstructionProps(error=0.010, duration=1.2e-6),
                (1,): _InstructionProps(error=0.020, duration=1.3e-6),
                (2,): _InstructionProps(error=0.030, duration=1.4e-6),
            },
        }

    def __getitem__(self, gate: str):
        return self._ops[gate]

    def build_coupling_map(self):
        return [(0, 1), (1, 2)]


class _QubitProps:
    def __init__(self, q: int) -> None:
        self.t1 = (50 + q) * 1e-6
        self.t2 = (70 + q) * 1e-6


class _Properties:
    last_update_date = "2026-05-03T00:00:00+00:00"

    def readout_error(self, q: int) -> float:
        return 0.01 * (q + 1)

    def qubit_property(self, q: int):
        return {
            "prob_meas1_prep0": (0.01 * (q + 1), None),
            "prob_meas0_prep1": (0.02 * (q + 1), None),
        }


class _Config:
    basis_gates = ["sx", "cz", "measure"]
    max_shots = 10_000
    memory = False
    qobd = False
    dt = 1e-9
    coupling_map = [(0, 1), (1, 2)]


class _Status:
    operational = True


class _Backend:
    name = "ibm_fake"
    simulator = False
    num_qubits = 3
    basis_gates = ["sx", "cz", "measure"]
    supported_instructions = ["sx", "cz", "measure"]
    coupling_map = [(0, 1), (1, 2)]
    target = _Target()
    description = "fake backend"

    def configuration(self):
        return _Config()

    def properties(self, refresh: bool = False):
        return _Properties()

    def qubit_properties(self, q: int):
        return _QubitProps(q)

    def status(self):
        return _Status()


class _Service:
    def __init__(self, backend: _Backend) -> None:
        self.backend_obj = backend

    def backends(self):
        return [self.backend_obj]

    def backend(self, _name: str):
        return self.backend_obj


def test_ibm_chip_characterization_uses_target_per_edge_errors():
    from uniqc.backend_adapter.task.adapters.ibm_adapter import _chip_characterization_from_backend

    chip = _chip_characterization_from_backend(_Backend(), backend_name="ibm_fake")

    edge_fids = {
        (item.qubit_u, item.qubit_v): item.gates[0].fidelity
        for item in chip.two_qubit_data
    }
    assert edge_fids[(0, 1)] == pytest.approx(0.959)
    assert edge_fids[(1, 2)] == pytest.approx(0.917)
    assert len(set(edge_fids.values())) == 2

    qubit_fids = [item.single_gate_fidelity for item in chip.single_qubit_data]
    assert qubit_fids == pytest.approx([0.999, 0.998, 0.997])


def test_ibm_backend_summary_uses_cached_per_edge_details_without_chip_cache():
    from uniqc.backend_adapter.backend_registry import _normalise_ibm
    from uniqc.backend_adapter.task.adapters.ibm_adapter import IBMAdapter
    from uniqc.gateway.api.backends import _backend_summary

    adapter = IBMAdapter.__new__(IBMAdapter)
    adapter._delegate = type("Delegate", (), {"_service": _Service(_Backend())})()

    raw = adapter.list_backends()
    backend = _normalise_ibm(raw)[0]
    summary = _backend_summary(backend, chip_meta={})

    edge_fids = {
        (edge["u"], edge["v"]): edge["fidelity"]
        for edge in summary["topology"]["edges"]
    }
    assert edge_fids[(0, 1)] == pytest.approx(0.959)
    assert edge_fids[(1, 2)] == pytest.approx(0.917)
    assert len(set(edge_fids.values())) == 2
