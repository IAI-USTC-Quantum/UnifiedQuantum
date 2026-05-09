"""07 — Matrix-product-state simulator on a long linear chain

[doc-require: ]
[doc-output-include: stdout, source]

MPS 引擎是一个线性拓扑、无噪声、能扩展到上百比特的模拟器（前提是中等纠缠）。两种
入口：

* ``MPSSimulator`` 直接 API；
* ``submit_task(backend="dummy:local:mps-linear-N:chi=K:cutoff=E:seed=S")`` 通过统一的
  任务接口（参数解析见 ``resolve_dummy_backend``）。
"""

from __future__ import annotations

from uniqc import Circuit
from uniqc.backend_adapter.dummy_backend import resolve_dummy_backend
from uniqc.backend_adapter.task_manager import submit_task, wait_for_result
from uniqc.simulator import MPSConfig, MPSSimulator


def build_brick_ghz(n: int) -> Circuit:
    c = Circuit(n)
    c.h(0)
    for i in range(n - 1):
        c.cnot(i, i + 1)
    for q in range(n):
        c.measure(q)
    return c


def main() -> None:
    n = 32

    print(f"== Direct MPSSimulator (N={n}) ==")
    circuit = build_brick_ghz(n)
    sim = MPSSimulator(MPSConfig(chi_max=64, svd_cutoff=1e-12, seed=2024))
    counts = sim.simulate_shots(circuit.originir, shots=400)
    print(f"  observed keys: {sorted(counts)}")
    print(f"  total shots:   {sum(counts.values())}")
    print(f"  max bond dim:  {sim.max_bond}")

    print(f"\n== dummy:local:mps-linear-{n} backend (chi=8, forces truncation) ==")
    task = submit_task(
        circuit,
        backend=f"dummy:local:mps-linear-{n}:chi=8:cutoff=1e-10",
        shots=400,
    )
    print("  result:", wait_for_result(task, timeout=60))

    print("\n== Parameter parsing ==")
    spec = resolve_dummy_backend("dummy:local:mps-linear-8:chi=16:cutoff=1e-8:seed=7")
    print("  identifier:       ", spec.identifier)
    print("  available_qubits: ", spec.available_qubits)
    print("  simulator_kwargs: ", spec.simulator_kwargs)


if __name__ == "__main__":
    main()
