"""Random circuit generators for cross-entropy benchmarking (XEB).

Generates 1-qubit and 2-qubit XEB circuits in OriginIR format
using the Circuit builder API.
"""

from __future__ import annotations

import math

from uniqc.circuit_builder import Circuit

__all__ = [
    "generate_1q_xeb_circuits",
    "generate_2q_xeb_circuit",
    "generate_parallel_2q_xeb_circuits",
]

# Random single-qubit gate pool for XEB
# Each entry: (gate_name, n_params)
_1Q_GATES = [
    ("H", 0),
    ("X", 0),
    ("Y", 0),
    ("Z", 0),
    ("S", 0),
    ("T", 0),
    ("RX", 1),
    ("RY", 1),
    ("RZ", 1),
]


def _random_gate(rng) -> tuple[str, float | None]:
    """Pick a random single-qubit gate and optionally a parameter."""
    name, n_params = rng.choice(_1Q_GATES)
    name = str(name)
    n_params = int(n_params)
    if n_params == 0:
        return name, None
    angle = rng.uniform(0, 2 * math.pi)
    return name, angle


def _add_random_layer(circuit: Circuit, qubits: list[int], rng) -> None:
    """Add one random single-qubit layer to the circuit."""
    for q in qubits:
        gate, angle = _random_gate(rng)
        if angle is not None:
            circuit.add_gate(gate, qubits=[q], params=[angle])
        else:
            circuit.add_gate(gate, qubits=[q])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_1q_xeb_circuits(
    qubit: int,
    depths: list[int],
    n_circuits: int = 50,
    seed: int | None = None,
) -> list[Circuit]:
    """Generate random 1-qubit XEB circuits.

    Each circuit consists of ``depth`` random single-qubit layers,
    followed by measurement. The circuits are designed to measure
    the per-layer depolarizing fidelity by fitting the exponential
    decay of the normalized linear XEB estimator as depth increases.

    Args:
        qubit: Qubit index to operate on.
        depths: List of circuit depths to generate (one circuit per depth
            is generated ``n_circuits`` times).
        n_circuits: Number of circuits to generate per depth.
        seed: Random seed for reproducibility.

    Returns:
        List of ``Circuit`` objects, one per (depth, circuit_index) pair.
        The total number of circuits is ``len(depths) * n_circuits``.
    """
    import numpy as np

    rng = np.random.default_rng(seed)
    circuits = []

    for depth in depths:
        for _ in range(n_circuits):
            c = Circuit(1)
            for _ in range(depth):
                _add_random_layer(c, [qubit], rng)
            c.measure(qubit)
            circuits.append(c)

    return circuits


def generate_2q_xeb_circuit(
    qubit_u: int,
    qubit_v: int,
    depth: int,
    entangler_gate: str = "CNOT",
    seed: int | None = None,
) -> Circuit:
    """Generate a single random 2-qubit XEB circuit.

    Each layer consists of:
      1. Random single-qubit gate on each qubit
      2. The specified entangling gate on the pair

    Args:
        qubit_u: First qubit index.
        qubit_v: Second qubit index.
        depth: Number of random layers (>= 1).
        entangler_gate: 2-qubit gate name (e.g. "CNOT", "CZ", "ISWAP").
        seed: Random seed for reproducibility.

    Returns:
        A single ``Circuit`` object.
    """
    import numpy as np

    rng = np.random.default_rng(seed)
    c = Circuit(2)

    for _ in range(depth):
        _add_random_layer(c, [qubit_u, qubit_v], rng)
        c.add_gate(entangler_gate, qubits=[qubit_u, qubit_v])

    c.measure(qubit_u)
    c.measure(qubit_v)
    return c


def generate_2q_xeb_circuits(
    qubit_u: int,
    qubit_v: int,
    depths: list[int],
    n_circuits: int = 50,
    entangler_gate: str = "CNOT",
    seed: int | None = None,
) -> list[Circuit]:
    """Generate random 2-qubit XEB circuits for a single qubit pair.

    Args:
        qubit_u: First qubit index.
        qubit_v: Second qubit index.
        depths: List of circuit depths.
        n_circuits: Number of circuits per depth.
        entangler_gate: 2-qubit gate name.
        seed: Random seed.

    Returns:
        List of ``Circuit`` objects.
    """
    circuits = []
    for depth in depths:
        for i in range(n_circuits):
            c = generate_2q_xeb_circuit(
                qubit_u, qubit_v, depth, entangler_gate, seed=seed + i if seed is not None else None
            )
            circuits.append(c)
    return circuits


def generate_parallel_2q_xeb_circuits(
    pairs: list[tuple[int, int]],
    depth: int,
    entangler_gates: dict[tuple[int, int], str],
    n_circuits: int = 50,
    seed: int | None = None,
) -> list[list[Circuit]]:
    """Generate parallel 2-qubit XEB circuits.

    All pairs are executed in parallel (within a single multi-qubit circuit)
    at each layer. This simulates full-chip parallel execution where
    disjoint pairs of qubits execute 2-qubit gates simultaneously.

    Args:
        pairs: List of qubit pairs to include in parallel.
        depth: Number of random layers per pair.
        entangler_gates: Mapping from pair to entangler gate name.
            Falls back to "CNOT" for any pair not in the dict.
        n_circuits: Number of parallel circuits to generate.
        seed: Random seed.

    Returns:
        List of lists of ``Circuit`` objects. Outer list: one circuit per
        ``n_circuits``. Inner list: one ``Circuit`` per pair (all measured
        in the same circuit object — a single multi-qubit circuit).
        Actually returns a list of Circuits where each Circuit operates on
        all qubits in the union of all pairs.
    """
    import numpy as np

    rng = np.random.default_rng(seed)
    # Collect all unique qubits
    all_qubits = sorted({q for pair in pairs for q in pair})
    n_total = len(all_qubits)
    # Build qubit index map
    qubit_map = {q: i for i, q in enumerate(all_qubits)}

    circuits = []
    for _ in range(n_circuits):
        c = Circuit(n_total)
        for _ in range(depth):
            # Random 1q layer on all qubits
            _add_random_layer(c, [qubit_map[q] for q in all_qubits], rng)
            # Parallel 2q layer
            for pu, pv in pairs:
                gate = entangler_gates.get((pu, pv), entangler_gates.get((pv, pu), "CNOT"))
                c.add_gate(gate, qubits=[qubit_map[pu], qubit_map[pv]])
        for i in range(n_total):
            c.measure(i)
        circuits.append(c)

    return circuits
