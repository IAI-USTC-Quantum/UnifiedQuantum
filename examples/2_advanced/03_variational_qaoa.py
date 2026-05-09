"""03 — Variational quantum algorithm: a tiny QAOA loop

[doc-require: ]
[doc-output-include: stdout, source]

最小可执行的 QAOA 演示：固定 1 层、单参数对，扫两个角度找最优。
真正的 VQA 训练循环在 ``examples/3_best_practices/07_variational_circuit.py``
和 ``examples/3_best_practices/08_torch_quantum_training.py``。
"""

from __future__ import annotations

import itertools

from uniqc import Circuit
from uniqc.simulator import OriginIR_Simulator


def qaoa_layer(gamma: float, beta: float) -> Circuit:
    c = Circuit(2)
    c.h(0)
    c.h(1)
    # cost (ZZ): exp(-i gamma Z0Z1) ≡ CNOT-RZ-CNOT
    c.cnot(0, 1)
    c.rz(1, 2 * gamma)
    c.cnot(0, 1)
    # mixer
    c.rx(0, 2 * beta)
    c.rx(1, 2 * beta)
    c.measure(0, 1)
    return c


def main() -> None:
    sim = OriginIR_Simulator()

    best = None
    for gamma, beta in itertools.product([0.2, 0.4, 0.6], [0.2, 0.4, 0.6]):
        counts = sim.simulate_shots(qaoa_layer(gamma, beta).originir, shots=512)
        # cost: <Z0 Z1> = P(00) + P(11) - P(01) - P(10), but we want max-cut → minimize.
        total = sum(counts.values()) or 1
        zz = (counts.get(0, 0) + counts.get(3, 0) - counts.get(1, 0) - counts.get(2, 0)) / total
        if best is None or zz < best[2]:
            best = (gamma, beta, zz)
        print(f"gamma={gamma:.2f} beta={beta:.2f} <ZZ>={zz:+.4f}")

    print("best:", best)


if __name__ == "__main__":
    main()
