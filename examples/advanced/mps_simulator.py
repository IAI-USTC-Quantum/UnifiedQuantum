"""Matrix-Product-State (MPS) simulator example.

Runs a 32-qubit GHZ-like brick circuit through ``MPSSimulator`` (direct API)
and the ``dummy:mps:linear-N`` backend (via :func:`uniqc.submit_task`). The
MPS engine is noiseless and restricted to nearest-neighbour 2-qubit gates on
an open chain, but it scales to hundreds of qubits when the entanglement is
moderate (low Schmidt rank).

Run::

    python examples/advanced/mps_simulator.py
"""

from __future__ import annotations

from uniqc import Circuit
from uniqc.backend_adapter.task_manager import submit_task, wait_for_result
from uniqc.simulator import MPSConfig, MPSSimulator


def build_brick_ghz(n: int) -> Circuit:
    """Linear GHZ circuit on ``n`` qubits, all gates nearest-neighbour."""
    c = Circuit(n)
    c.h(0)
    for i in range(n - 1):
        c.cnot(i, i + 1)
    for q in range(n):
        c.measure(q, q)
    return c


def main() -> None:
    n = 32

    print(f"=== Direct MPSSimulator API (N={n}) ===")
    circuit = build_brick_ghz(n)
    sim = MPSSimulator(MPSConfig(chi_max=64, svd_cutoff=1e-12, seed=2024))
    counts = sim.simulate_shots(circuit.originir, shots=400)
    # GHZ: only all-zeros (key 0) and all-ones (key 2**n-1) survive.
    print(f"  observed keys: {sorted(counts.keys())}")
    print(f"  total shots:   {sum(counts.values())}")
    print(f"  max bond dim:  {sim.max_bond}")
    print(f"  truncations:   {len(sim.truncation_errors)} (max={max(sim.truncation_errors or [0]):.1e})")

    print(f"\n=== dummy:mps:linear-{n} backend (chi=8 forces truncation) ===")
    task = submit_task(
        circuit,
        backend=f"dummy:mps:linear-{n}:chi=8:cutoff=1e-10",
        shots=400,
    )
    result = wait_for_result(task, timeout=60)
    print(f"  result counts: {result}")

    print("\n=== Parameter parsing ===")
    from uniqc.backend_adapter.dummy_backend import resolve_dummy_backend

    spec = resolve_dummy_backend("dummy:mps:linear-8:chi=16:cutoff=1e-8:seed=7")
    print(f"  identifier:        {spec.identifier}")
    print(f"  description:       {spec.description}")
    print(f"  available_qubits:  {spec.available_qubits}")
    print(f"  topology:          {spec.available_topology}")
    print(f"  simulator_kwargs:  {spec.simulator_kwargs}")


if __name__ == "__main__":
    main()
