"""XEB: Cross-Entropy Benchmarking module."""

from .benchmarker import XEBenchmarker
from .circuits import (
    generate_1q_xeb_circuits,
    generate_2q_xeb_circuit,
    generate_2q_xeb_circuits,
    generate_parallel_2q_xeb_circuits,
)
from .fitter import compute_hellinger_fidelity, compute_linear_xeb, fit_exponential
from .parallel_cz import (
    PairCircuitFit,
    PairDecay,
    ParallelCZBenchmarker,
    ProbeCircuit,
    Schedule,
    build_parallel_cz_xeb_circuit,
    build_parallel_cz_xeb_corpus,
    fit_pair_decays,
    pair_ideal_probs,
    pair_marginal_counts,
    per_pair_F_XEB,
)
from .patterns import ParallelPatternGenerator, ParallelPatternResult
from .topology import (
    ChipTopologyView,
    Region,
    parallel_patterns,
    pick_chain_region,
    pick_region,
    three_color_chip,
)

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
    # Parallel-CZ XEB (chip pre-flight)
    "ChipTopologyView",
    "Region",
    "pick_region",
    "pick_chain_region",
    "parallel_patterns",
    "three_color_chip",
    "Schedule",
    "ProbeCircuit",
    "PairCircuitFit",
    "PairDecay",
    "build_parallel_cz_xeb_circuit",
    "build_parallel_cz_xeb_corpus",
    "pair_marginal_counts",
    "pair_ideal_probs",
    "per_pair_F_XEB",
    "fit_pair_decays",
    "ParallelCZBenchmarker",
]
