"""Smoke-test the complete ``unified-quantum[pytorch]`` installation."""

from __future__ import annotations

import math
from importlib.metadata import version

import torch
import torchquantum as tq

from uniqc import Circuit, expectation
from uniqc.simulator import TorchQuantumSimulator


def main() -> None:
    assert version("torchquantum-ng")

    theta = torch.tensor(0.25, requires_grad=True)
    circuit = Circuit(1)
    circuit.ry(0, theta)
    value = expectation(circuit, [("Z", 1.0)], backend="virtual")
    value.backward()
    assert theta.grad is not None
    assert math.isclose(theta.grad.item(), -math.sin(0.25), rel_tol=0.0, abs_tol=1e-5)

    device = tq.QuantumDevice(n_wires=2, bsz=1, device="cpu")
    device.h(wires=0)
    device.cnot(wires=[0, 1])
    assert tuple(device.states.shape) == (1, 2, 2)

    tq_simulator = TorchQuantumSimulator()
    bell = Circuit(2)
    bell.h(0)
    bell.cnot(0, 1)
    zz = tq_simulator.expectation(bell.opcode_list, [("ZZ", 1.0)]).item()
    assert math.isclose(zz, 1.0, rel_tol=0.0, abs_tol=1e-5)

    print(
        "pytorch extra smoke passed:",
        f"torch={torch.__version__}",
        f"torchquantum-ng={version('torchquantum-ng')}",
    )


if __name__ == "__main__":
    main()
