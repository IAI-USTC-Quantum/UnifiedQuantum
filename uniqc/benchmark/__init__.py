"""Reproducible NISQ benchmark entries for UnifiedQuantum.

This package provides two benchmark entries aligned with the NISQ-framework
acceptance items of the project:

- :mod:`uniqc.benchmark.quantum_volume` — reproducible Quantum Volume (QV)
  model-circuit generation, heavy-output evaluation, and pass/fail judgement.
- :mod:`uniqc.benchmark.throughput` — local compile/execute throughput
  measurement (circuits per hour at a fixed shots-per-circuit budget).

Both entries are deterministic given a seed and run entirely on the local
simulator stack; they never submit cloud tasks.
"""

from uniqc.benchmark.quantum_volume import (
    QVRunResult,
    QVTrialResult,
    build_qv_model_circuit,
    heavy_outputs_from_probabilities,
    run_quantum_volume,
)
from uniqc.benchmark.throughput import (
    ThroughputResult,
    build_random_nisq_circuit,
    run_throughput_benchmark,
)

__all__ = [
    "QVTrialResult",
    "QVRunResult",
    "build_qv_model_circuit",
    "heavy_outputs_from_probabilities",
    "run_quantum_volume",
    "ThroughputResult",
    "build_random_nisq_circuit",
    "run_throughput_benchmark",
]
