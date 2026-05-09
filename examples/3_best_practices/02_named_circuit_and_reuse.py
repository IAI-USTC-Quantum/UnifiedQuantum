"""02 — Named Circuit 与可复用线路

[doc-require: matplotlib]
[doc-output-include: stdout, figures, source]

用命名寄存器和 ``@circuit_def`` 组织可复用子线路，再组合成一个 4-qubit GHZ-like 电路。
"""

from __future__ import annotations

import math

import matplotlib.pyplot as plt

from uniqc import Circuit, circuit_def
from uniqc.simulator import OriginIR_Simulator


def probability_dict(values):
    n = int(round(math.log2(len(values)))) if values else 0
    return {
        format(i, f"0{n}b"): float(p)
        for i, p in enumerate(values)
        if abs(float(p)) > 1e-12
    }


def plot_probs(probs, title):
    labels = list(probs)
    values = [probs[k] for k in labels]
    fig, ax = plt.subplots(figsize=(6, 3.4))
    ax.bar(labels, values, color="#3267a8")
    ax.set_ylim(0, max(1.0, max(values, default=0) * 1.2))
    ax.set_xlabel("bitstring")
    ax.set_ylabel("probability")
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()


@circuit_def(name="bell_pair", qregs={"q": 2})
def bell_pair(circ, q):
    circ.h(q[0])
    circ.cnot(q[0], q[1])
    return circ


@circuit_def(name="rz_layer", qregs={"q": 4}, params=["angle"])
def rz_layer(circ, q, angle):
    for i in range(4):
        circ.rz(q[i], angle)
    return circ


def main() -> None:
    circuit = Circuit(qregs={"data": 4})
    data = circuit.get_qreg("data")

    bell_pair(circuit, qreg_mapping={"q": [data[0], data[1]]})
    bell_pair(circuit, qreg_mapping={"q": [data[2], data[3]]})
    circuit.cnot(data[1], data[2])
    rz_layer(
        circuit,
        qreg_mapping={"q": [data[0], data[1], data[2], data[3]]},
        param_values={"angle": 0.25},
    )
    circuit.measure(0, 1, 2, 3)

    print("DEF export:")
    print(bell_pair.to_originir_def())
    print("operations:", len(circuit.opcode_list))

    probs = probability_dict(OriginIR_Simulator().simulate_pmeasure(circuit.originir))
    print("non-zero states:", probs)
    plot_probs(probs, "Named circuit result")


if __name__ == "__main__":
    main()
