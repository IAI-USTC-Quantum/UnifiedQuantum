"""Tests for simulator factory helpers."""

import pytest

import warnings

import pytest

from uniqc.simulator import OriginIR_Simulator, QASM_Simulator, create_simulator, get_simulator
from uniqc.simulator.torchquantum_simulator import TORCHQUANTUM_AVAILABLE, TorchQuantumSimulator
from uniqc.simulator.torchquantum_simulator import TORCHQUANTUM_AVAILABLE, TorchQuantumSimulator


def test_create_simulator_originir_statevector():
    sim = create_simulator(backend="statevector")
    assert isinstance(sim, OriginIR_Simulator)


def test_create_simulator_qasm_density_alias():
    sim = create_simulator(backend="density_matrix", program_type="qasm")
    assert isinstance(sim, QASM_Simulator)


def test_get_simulator_delegates_to_create_simulator():
    sim = get_simulator(program_type="originir", backend_type="statevector")
    assert isinstance(sim, OriginIR_Simulator)


def test_get_backend_deprecated():
    from uniqc.simulator import get_backend

    with warnings.catch_warnings():
        warnings.simplefilter("always")
        sim = get_backend(program_type="originir", backend_type="statevector")
    assert isinstance(sim, OriginIR_Simulator)


def test_create_simulator_torchquantum_backend():
    if TORCHQUANTUM_AVAILABLE:
        sim = create_simulator(backend="torchquantum")
        assert isinstance(sim, TorchQuantumSimulator)
    else:
        with pytest.raises(ImportError, match="TorchQuantum backend requires"):
            create_simulator(backend="torchquantum")
