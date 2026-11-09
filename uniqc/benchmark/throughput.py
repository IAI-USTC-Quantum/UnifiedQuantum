"""Local compile/execute throughput benchmark for the NISQ framework.

Measures how many quantum circuits per hour the local UniQC pipeline can
compile and execute at a fixed shots-per-circuit budget (the acceptance
configuration is 1000 shots per circuit on average, >= 30,000 circuits per
hour).

Timed pipeline (the "compile/execute" boundary), per circuit:

1. **Compile** — ``Circuit`` -> OriginIR text -> ``Simulator.simulate_preprocess``
   (parse, opcode conversion, qubit/topology constraint validation).
2. **Execute** — exact statevector simulation (``simulate_pmeasure``) plus
   multinomial sampling of the configured number of shots from the outcome
   distribution.

Explicitly **outside** the timed window: interpreter/process startup, result
persistence (the SQLite task store), report serialisation and file I/O.  The
``backend_id`` selects the local simulator fixture; the measurement never
submits cloud tasks.

All circuit inputs are generated deterministically from one seed, so a
reported number is tied to a reproducible input set.
"""

from __future__ import annotations

import dataclasses
import os
import platform
import time
from collections.abc import Callable
from importlib import metadata
from typing import Any

import numpy as np

__all__ = [
    "ThroughputResult",
    "build_random_nisq_circuit",
    "run_throughput_benchmark",
]

_ONE_QUBIT_ROTATIONS = ("rx", "ry", "rz")
_TWO_QUBIT_GATES = ("cnot", "cz")


def build_random_nisq_circuit(
    n_qubits: int,
    depth: int,
    seed: int,
    *,
    entangler_edges: list[tuple[int, int]] | None = None,
):
    """Build one seeded random NISQ circuit (rotations + pairwise entanglers).

    Layer structure: each qubit receives one random rotation gate with a
    random angle, then entanglers pair the qubits — either over a random
    permutation (all-to-all, the default) or over a random matching drawn
    from ``entangler_edges`` (for topology-constrained line/grid fixtures).
    This is a representative variational-algorithm workload: no known
    structure, and full-width measurement.
    """
    if n_qubits < 1:
        raise ValueError(f"n_qubits must be >= 1, got {n_qubits}")
    if depth < 1:
        raise ValueError(f"depth must be >= 1, got {depth}")

    from uniqc.circuit_builder.qcircuit import Circuit

    rng = np.random.default_rng(seed)
    circuit = Circuit()
    edges = [
        (int(edge[0]), int(edge[1]))
        for edge in (entangler_edges or [])
        if int(edge[0]) < n_qubits and int(edge[1]) < n_qubits
    ]
    for _layer in range(depth):
        for qubit in range(n_qubits):
            gate = _ONE_QUBIT_ROTATIONS[int(rng.integers(len(_ONE_QUBIT_ROTATIONS)))]
            angle = float(rng.uniform(-np.pi, np.pi))
            getattr(circuit, gate)(qubit, angle)
        if edges:
            order = rng.permutation(len(edges))
            used: set[int] = set()
            pairs = []
            for index in order:
                q0, q1 = edges[index]
                if q0 not in used and q1 not in used:
                    pairs.append((q0, q1))
                    used.update((q0, q1))
        else:
            permutation = rng.permutation(n_qubits)
            pairs = [(int(permutation[i]), int(permutation[i + 1])) for i in range(0, n_qubits - 1, 2)]
        for q0, q1 in pairs:
            gate = _TWO_QUBIT_GATES[int(rng.integers(len(_TWO_QUBIT_GATES)))]
            getattr(circuit, gate)(q0, q1)
    circuit.measure(*range(n_qubits))
    return circuit


@dataclasses.dataclass(frozen=True)
class ThroughputResult:
    """Measured local compile/execute throughput over a seeded input set."""

    circuits: int
    n_qubits: int
    depth: int
    shots: int
    seed: int
    backend_id: str
    generator_mode: str
    compile_seconds: float
    execute_seconds: float
    total_seconds: float
    circuits_per_hour: float
    compile_circuits_per_hour: float
    execute_circuits_per_hour: float
    environment: dict[str, Any]

    @property
    def meets_30000_per_hour(self) -> bool:
        return self.circuits_per_hour >= 30_000.0

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "benchmark": "local_compile_execute_throughput",
            "criterion": "circuits/hour >= 30000 at the configured shots-per-circuit; boundary = OriginIR parse/preprocess + statevector simulate + shot sampling",
            "input_set": {
                "generator": "uniqc.benchmark.throughput.build_random_nisq_circuit",
                "generator_mode": self.generator_mode,
                "circuits": self.circuits,
                "n_qubits": self.n_qubits,
                "depth": self.depth,
                "shots_per_circuit": self.shots,
                "seed": self.seed,
            },
            "backend_id": self.backend_id,
            "timing": {
                "compile_seconds": self.compile_seconds,
                "execute_seconds": self.execute_seconds,
                "total_seconds": self.total_seconds,
                "circuits_per_hour": self.circuits_per_hour,
                "compile_circuits_per_hour": self.compile_circuits_per_hour,
                "execute_circuits_per_hour": self.execute_circuits_per_hour,
            },
            "meets_30000_per_hour": self.meets_30000_per_hour,
            "environment": self.environment,
        }


def _load_average_1min() -> float | None:
    """Return the 1-minute load average, or ``None`` where the OS lacks it."""
    getloadavg = getattr(os, "getloadavg", None)
    if getloadavg is None:
        return None
    try:
        return float(getloadavg()[0])
    except OSError:
        return None


def _environment_info() -> dict[str, Any]:
    def version_of(dist: str) -> str | None:
        try:
            return metadata.version(dist)
        except metadata.PackageNotFoundError:
            return None

    return {
        "python": platform.python_version(),
        "machine": platform.machine(),
        "processor": platform.processor() or None,
        "cpu_count_logical": os.cpu_count(),
        "load_average_1min": _load_average_1min(),
        "numpy": version_of("numpy"),
        "unified-quantum": version_of("unified-quantum"),
        "uniqc-cppsimulator": version_of("uniqc-cppsimulator"),
        "cpu_backend": "uniqc_cpp.StatevectorSimulator (via uniqc.Simulator)",
        "dependency_source": "PyPI wheel uniqc-cppsimulator>=1.0.1,<2 (core dependency of unified-quantum)",
    }


def run_throughput_benchmark(
    *,
    circuits: int,
    n_qubits: int,
    depth: int,
    shots: int = 1000,
    seed: int = 0,
    backend_id: str = "dummy:local:simulator",
    simulator_factory: Callable[[], Any] | None = None,
    progress: Callable[[int], None] | None = None,
) -> ThroughputResult:
    """Time the local compile/execute pipeline over a seeded circuit set.

    Args:
        circuits: Number of circuits in the input set.
        n_qubits: Qubits per circuit.
        depth: Entangling-layer depth per circuit.
        shots: Shots sampled per circuit (default 1000, the acceptance
            configuration).
        seed: Base seed; circuit *i* uses ``seed + i``.
        backend_id: Recorded backend identity (execution itself runs on the
            local simulator stack).  Topology-constrained fixtures
            (``dummy:local:virtual-line-N`` / ``virtual-grid-RxC``) switch
            the generator to nearest-neighbour entanglers automatically.
        simulator_factory: Override simulator construction (tests use this to
            inject fakes).  Defaults to ``uniqc.Simulator`` with the backend's
            resolved qubit/topology constraints.
        progress: Optional callback invoked with the completed circuit count.

    Returns:
        A :class:`ThroughputResult` with the measured wall-clock times and
        derived circuits-per-hour rates.
    """
    if circuits < 1:
        raise ValueError(f"circuits must be >= 1, got {circuits}")
    if shots < 1:
        raise ValueError(f"shots must be >= 1, got {shots}")

    from uniqc.backend_adapter.dummy_backend import resolve_dummy_backend
    from uniqc.simulator import Simulator

    spec = resolve_dummy_backend(backend_id, allow_fetch=False)
    if spec.simulator_kind == "mps":
        raise ValueError(
            "The throughput benchmark targets the default statevector path; "
            f"got simulator_kind='mps' for {backend_id!r}."
        )
    entangler_edges = [(int(u), int(v)) for u, v in (spec.available_topology or [])]

    rng = np.random.default_rng(seed + 999_983)  # shot-sampling stream, disjoint from circuit seeds

    compile_seconds = 0.0
    execute_seconds = 0.0
    for index in range(circuits):
        circuit = build_random_nisq_circuit(n_qubits, depth, seed + index, entangler_edges=entangler_edges)
        originir = circuit.originir
        sim = (
            simulator_factory()
            if simulator_factory is not None
            else Simulator(
                backend_type="statevector",
                available_qubits=spec.available_qubits or None,
                available_topology=spec.available_topology or None,
            )
        )

        start = time.perf_counter()
        program_body, measure_qubits = sim.simulate_preprocess(originir)
        compile_done = time.perf_counter()
        compile_seconds += compile_done - start

        # Execute: exact statevector probabilities + seeded shot sampling.
        probabilities = np.asarray(
            sim.opcode_simulator.simulate_opcodes_pmeasure(sim.qubit_num, program_body, measure_qubits),
            dtype=float,
        )
        _ = rng.multinomial(shots, probabilities / probabilities.sum())
        execute_seconds += time.perf_counter() - compile_done

        if progress is not None:
            progress(index + 1)

    total_seconds = compile_seconds + execute_seconds
    if total_seconds <= 0:  # pragma: no cover - timer resolution guard
        total_seconds = 1e-12
    return ThroughputResult(
        circuits=circuits,
        n_qubits=n_qubits,
        depth=depth,
        shots=shots,
        seed=seed,
        backend_id=spec.identifier,
        generator_mode=(
            f"topology_matching over {len(entangler_edges)} resolved edges"
            if entangler_edges
            else "random_permutation_all_to_all"
        ),
        compile_seconds=compile_seconds,
        execute_seconds=execute_seconds,
        total_seconds=total_seconds,
        circuits_per_hour=circuits * 3600.0 / total_seconds,
        compile_circuits_per_hour=circuits * 3600.0 / max(compile_seconds, 1e-12),
        execute_circuits_per_hour=circuits * 3600.0 / max(execute_seconds, 1e-12),
        environment=_environment_info(),
    )
