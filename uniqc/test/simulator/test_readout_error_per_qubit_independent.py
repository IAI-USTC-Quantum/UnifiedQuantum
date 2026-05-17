"""Regression test for per-qubit independence of the single-shot readout RNG.

Before the C-2 fix, ``_add_readout_error_single_shot`` drew a single random
number ``r`` once before the per-qubit loop and reused it for every qubit.
That meant either *all* qubits flipped or *none* flipped on a given shot.
With ``p = 0.5`` flip probability on every qubit of a 5-qubit identity
circuit, the buggy code only ever produced ``00000`` or ``11111``; the
fixed code draws a fresh ``r`` per qubit, producing a roughly uniform
distribution over all 32 bitstrings.
"""

from __future__ import annotations

from uniqc.circuit_builder import Circuit
from uniqc.simulator import NoisySimulator, seed


def test_single_shot_readout_error_is_per_qubit_independent() -> None:
    n = 5
    shots = 4096
    # Identity circuit on 5 qubits (no gates needed — they stay in |0⟩).
    circuit = Circuit(n)
    circuit.measure(*range(n))

    # Symmetric 50% flip on every qubit, both directions.
    readout_error = {q: [0.5, 0.5] for q in range(n)}

    seed(20240101)
    sim = NoisySimulator(backend_type="statevector", readout_error=readout_error)

    all_zero = 0
    all_one = (1 << n) - 1
    mixed = 0
    distinct = set()
    for _ in range(shots):
        out = sim.simulate_single_shot(circuit.originir)
        distinct.add(out)
        if out != all_zero and out != all_one:
            mixed += 1

    # Per-qubit independence ⇒ most outcomes are neither all-0 nor all-1.
    # The expected mixed fraction is 30/32 ≈ 0.94; we require comfortably
    # more than half.  Under the buggy (shared-RNG) implementation this
    # count is exactly 0.
    assert mixed > 0.5 * shots, (
        f"Expected most outcomes to be mixed-parity, got mixed={mixed} of {shots}; "
        f"distinct outcomes seen: {len(distinct)}"
    )
    # We should also see many distinct bitstrings (buggy code yields only 2).
    assert len(distinct) > 2
