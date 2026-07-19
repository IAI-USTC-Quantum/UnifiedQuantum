"""Tests for simulator error models."""

from __future__ import annotations

import math

import pytest

from uniqc.simulator.error_model import Depolarizing, ErrorLoader_GenericError, ThermalRelaxation


def test_error_loader_process_opcodes_resets_between_circuits():
    """Reusable error loaders should not retain prior circuit opcodes."""
    error_loader = ErrorLoader_GenericError([Depolarizing(0.01)])

    error_loader.process_opcodes([("X", 0, None, None, False, None)])
    error_loader.process_opcodes([("HADAMARD", 0, None, None, False, None)])

    assert error_loader.opcodes == [
        ("HADAMARD", 0, None, None, False, None),
        ("Depolarizing", 0, None, 0.01, None, None),
    ]


class TestThermalRelaxation:
    def test_t1_and_t2_rates(self):
        t, t1, t2 = 80.0, 50_000.0, 40_000.0
        model = ThermalRelaxation(t1, t2, t)
        gamma = 1.0 - math.exp(-t / t1)
        p_phi = 0.5 * (1.0 - math.exp(-t * (1.0 / t2 - 1.0 / (2.0 * t1))))
        assert model.generate_error_opcode(0) == [
            ("AmplitudeDamping", 0, None, pytest.approx(gamma), None, None),
            ("PhaseFlip", 0, None, pytest.approx(p_phi), None, None),
        ]

    def test_t1_only_emits_amplitude_damping(self):
        model = ThermalRelaxation(50_000.0, None, 100.0)
        opcodes = model.generate_error_opcode([0, 1])
        assert opcodes == [
            ("AmplitudeDamping", 0, None, pytest.approx(1.0 - math.exp(-100.0 / 50_000.0)), None, None),
            ("AmplitudeDamping", 1, None, pytest.approx(1.0 - math.exp(-100.0 / 50_000.0)), None, None),
        ]

    def test_t2_only_emits_pure_dephasing(self):
        t, t2 = 60.0, 30_000.0
        model = ThermalRelaxation(None, t2, t)
        p_phi = 0.5 * (1.0 - math.exp(-t / t2))
        assert model.generate_error_opcode(0) == [
            ("PhaseFlip", 0, None, pytest.approx(p_phi), None, None),
        ]

    def test_per_qubit_maps_and_missing_entries(self):
        model = ThermalRelaxation({0: 50_000.0}, {1: 40_000.0}, 100.0)
        # Qubit 0 has only T1, qubit 1 only T2, qubit 2 nothing.
        opcodes = model.generate_error_opcode([0, 1, 2])
        assert opcodes == [
            ("AmplitudeDamping", 0, None, pytest.approx(1.0 - math.exp(-100.0 / 50_000.0)), None, None),
            ("PhaseFlip", 1, None, pytest.approx(0.5 * (1.0 - math.exp(-100.0 / 40_000.0))), None, None),
        ]

    def test_requires_at_least_one_time_constant(self):
        with pytest.raises(ValueError, match="at least one of t1_ns / t2_ns"):
            ThermalRelaxation(None, None, 100.0)

    def test_requires_positive_gate_time(self):
        with pytest.raises(ValueError, match="positive gate_time_ns"):
            ThermalRelaxation(50_000.0, None, 0.0)

    def test_rejects_t2_above_2t1_at_generation(self):
        model = ThermalRelaxation(10_000.0, 30_000.0, 100.0)
        with pytest.raises(ValueError, match=r"T2 <= 2\*T1"):
            model.generate_error_opcode(0)

    def test_exported_from_simulator_package(self):
        from uniqc.simulator import ThermalRelaxation as Exported

        assert Exported is ThermalRelaxation
