from pathlib import Path

import pytest

from uniqc.backend_adapter.backend_info import BackendInfo, Platform
from uniqc.circuit_builder import Circuit
from uniqc.visualization.timeline import (
    TimelineDurationError,
    circuit_to_html,
    plot_time_line_html,
    schedule_circuit,
)


def test_logical_circuit_requires_duration_data():
    circuit = Circuit()
    circuit.h(0)

    with pytest.raises(TimelineDurationError, match="No duration is available"):
        schedule_circuit(circuit)


def test_logical_circuit_is_compiled_to_basis_before_scheduling():
    circuit = Circuit()
    circuit.h(0)
    circuit.x(1)
    circuit.barrier(0, 1)
    circuit.cnot(0, 1)
    circuit.rz(0, 0.25)
    circuit.measure(0, 1)

    schedule = schedule_circuit(
        circuit,
        gate_durations={
            "SX": 50,
            "CZ": 80,
            "measure": 300,
        },
    )

    non_measure_names = {gate.name for gate in schedule.gates if gate.name != "MEASURE"}
    assert non_measure_names <= {"SX", "RZ", "CZ", "BARRIER"}

    barrier = next(gate for gate in schedule.gates if gate.name == "BARRIER")
    barrier_index = schedule.gates.index(barrier)
    assert all(gate.end <= barrier.start for gate in schedule.gates[:barrier_index])
    assert all(gate.start >= barrier.start for gate in schedule.gates[barrier_index + 1 :])
    assert all(gate.duration == 0 for gate in schedule.gates if gate.name == "RZ")
    assert all(gate.duration == 50 for gate in schedule.gates if gate.name == "SX")
    assert all(gate.duration == 80 for gate in schedule.gates if gate.name == "CZ")


def test_backend_info_generic_durations_are_used():
    circuit = Circuit()
    circuit.sx(0)
    circuit.cz(0, 1)

    backend = BackendInfo(
        platform=Platform.DUMMY,
        name="timing-test",
        extra={"single_qubit_gate_time": 30, "two_qubit_gate_time": 90},
    )

    schedule = schedule_circuit(circuit, backend_info=backend)
    assert [(gate.name, gate.start, gate.duration) for gate in schedule.gates] == [
        ("SX", 0.0, 30.0),
        ("CZ", 30.0, 90.0),
    ]


def test_explicit_pulse_data_does_not_require_durations():
    pulse = [{"RPhi": [0, 45.0, 90.0, 0]}, {"CZ": [0, 1, 30]}]

    schedule = schedule_circuit(pulse)
    assert [(gate.name, gate.start) for gate in schedule.gates] == [("RPhi90", 0.0), ("CZ", 30.0)]


def test_static_html_renderers_include_tooltips(tmp_path: Path):
    circuit = Circuit()
    circuit.h(0)
    circuit.cnot(0, 1)

    circuit_html = circuit_to_html(circuit)
    assert "<title>" in circuit_html
    assert "gate: H" in circuit_html

    timeline_path = tmp_path / "timeline.html"
    timeline_html = plot_time_line_html(
        circuit,
        timeline_path,
        gate_durations={"1q": 20, "2q": 80},
    )
    assert timeline_path.exists()
    assert "gate: CZ" in timeline_html
    assert "gate: SX" in timeline_html
