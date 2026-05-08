"""XEB: Cross-Entropy Benchmarking module."""

from .benchmarker import XEBenchmarker
from .circuits import (
    generate_1q_xeb_circuits,
    generate_2q_xeb_circuit,
    generate_2q_xeb_circuits,
    generate_parallel_2q_xeb_circuits,
)
from .fitter import compute_hellinger_fidelity, compute_linear_xeb, fit_exponential
from .patterns import ParallelPatternGenerator, ParallelPatternResult

__all__ = [
    "XEBenchmarker",
    "generate_1q_xeb_circuits",
    "generate_2q_xeb_circuit",
    "generate_2q_xeb_circuits",
    "generate_parallel_2q_xeb_circuits",
    "compute_hellinger_fidelity",
    "compute_linear_xeb",
    "fit_exponential",
    "ParallelPatternGenerator",
    "ParallelPatternResult",
]
