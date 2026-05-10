"""Tests for simulator factory helpers."""

import warnings

import pytest

from uniqc.simulator import Simulator, NoisySimulator, create_simulator, get_simulator
from uniqc.simulator.torchquantum_simulator import TORCHQUANTUM_AVAILABLE, TorchQuantumSimulator


def test_create_simulator_statevector():
    sim = create_simulator(backend="statevector")
    assert isinstance(sim, Simulator)


def test_create_simulator_density_alias():
    sim = create_simulator(backend="density_matrix")
    assert isinstance(sim, Simulator)


def test_create_simulator_noisy():
    sim = create_simulator(backend="density_matrix", noise=True)
    assert isinstance(sim, NoisySimulator)


def test_get_simulator_delegates_to_create_simulator():
    sim = get_simulator(backend_type="statevector")
    assert isinstance(sim, Simulator)


def test_get_backend_deprecated():
    from uniqc.simulator import get_backend

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        sim = get_backend(backend_type="statevector")
    assert isinstance(sim, Simulator)
    assert any("deprecated" in str(warning.message).lower() for warning in w)


def test_create_simulator_torchquantum_backend():
    if TORCHQUANTUM_AVAILABLE:
        sim = create_simulator(backend="torchquantum")
        assert isinstance(sim, TorchQuantumSimulator)
    else:
        with pytest.raises(ImportError, match="TorchQuantum backend requires"):
            create_simulator(backend="torchquantum")
