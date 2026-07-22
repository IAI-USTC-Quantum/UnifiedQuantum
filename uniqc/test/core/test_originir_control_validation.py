"""Range validation for OriginIR control qubits."""

from __future__ import annotations

import pytest

from uniqc.compile.originir.originir_base_parser import OriginIR_BaseParser


def test_inline_control_qubit_must_be_in_qinit_range() -> None:
    originir = """
QINIT 2
CREG 0
X q[0] controlled_by(q[999])
"""

    with pytest.raises(ValueError, match=r"Control qubit exceeds.*QINIT 2"):
        OriginIR_BaseParser().parse(originir)


def test_circuit_width_includes_explicit_control_qubits() -> None:
    from uniqc.circuit_builder import Circuit

    circuit = Circuit()
    circuit.add_gate("X", 0, control_qubits=[3])

    assert circuit.qubit_num == 4
    assert circuit.originir.startswith("QINIT 4\n")


@pytest.mark.requires_cpp
@pytest.mark.parametrize("simulator_name", ["StatevectorSimulator", "DensityOperatorSimulator"])
def test_cpp_simulator_rejects_out_of_range_global_control(simulator_name: str) -> None:
    uniqc_cpp = pytest.importorskip("uniqc_cpp")
    simulator = getattr(uniqc_cpp, simulator_name)()
    simulator.init_n_qubit(2)

    with pytest.raises(ValueError, match=r"control_qubit = 999"):
        simulator.x(0, [999], False)
