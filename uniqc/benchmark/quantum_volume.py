"""Reproducible Quantum Volume (QV) benchmark entry.

Implements the model-circuit definition and heavy-output criterion of
Cross *et al.*, "Validating quantum computers using randomized model
circuits" (Phys. Rev. A 100, 032328, 2019):

- A QV model circuit of width ``m`` and depth ``m`` consists of ``m`` layers;
  each layer applies a uniformly random qubit permutation followed by
  Haar-random SU(4) blocks on neighbouring pairs.
- Heavy outputs are the basis states whose ideal output probability exceeds
  the median of the full distribution.
- One trial succeeds when the observed heavy-output frequency ``h`` exceeds
  2/3 with two-sigma confidence: ``h - 2*sqrt(h*(1-h)/shots) > 2/3``.
- The run succeeds when the mean heavy-output frequency over all trials
  exceeds 2/3 with two-sigma confidence
  (``mean_h - 2*sqrt(mean_h*(1-mean_h)/(trials*shots)) > 2/3``);
  on success the tested backend is credited with ``QV = 2**m``.

SU(4) blocks are decomposed into the OriginIR native gates ``U3``/``CNOT``
with the (exact, CNOT-optimal) two-qubit Weyl decomposition shipped with the
core qiskit dependency.  Everything — model circuits, ideal probabilities,
and sampled shots — is derived from a single explicit seed, so a run is
bit-for-bit reproducible.

This module is a *local* software entry: it executes on the local simulator
stack (``uniqc.Simulator`` / any dummy backend) and never submits cloud
tasks.  Evidence gathered here certifies the software pipeline, not any real
quantum processor.
"""

from __future__ import annotations

import dataclasses
from typing import Any

import numpy as np

__all__ = [
    "QVTrialResult",
    "QVRunResult",
    "build_qv_model_circuit",
    "haar_su4",
    "heavy_outputs_from_probabilities",
    "run_quantum_volume",
]

_HEAVY_THRESHOLD = 2.0 / 3.0
_DECOMPOSER: Any = None


def haar_su4(rng: np.random.Generator) -> np.ndarray:
    """Draw a Haar-random SU(4) matrix."""
    z = rng.normal(size=(4, 4)) + 1j * rng.normal(size=(4, 4))
    q, r = np.linalg.qr(z)
    q = q * (np.diagonal(r) / np.abs(np.diagonal(r)))
    q = q * np.linalg.det(q) ** (-0.25)
    return q


def _decomposer() -> Any:
    """Cached CNOT-optimal two-qubit Weyl decomposer (3 CNOTs, 8 U3 gates)."""
    global _DECOMPOSER
    if _DECOMPOSER is None:
        from qiskit.circuit.library import CXGate
        from qiskit.synthesis import TwoQubitBasisDecomposer

        _DECOMPOSER = TwoQubitBasisDecomposer(CXGate(), basis_fidelity=1.0)
    return _DECOMPOSER


def _su4_to_ops(unitary: np.ndarray) -> list[tuple[str, tuple[int, int], tuple[float, ...]]]:
    """Decompose one SU(4) into ``[("U3"/"CNOT", (qubits), (params, ...)), ...]``.

    The decomposition is exact up to global phase; the global phase is
    dropped — it does not affect measurement statistics and OriginIR has no
    phase gate for this purpose.
    """
    qc = _decomposer()(unitary)
    ops: list[tuple[str, tuple[int, int], tuple[float, ...]]] = []
    for inst in qc.data:
        name = inst.operation.name
        qubits = tuple(qc.find_bit(bit).index for bit in inst.qubits)
        params = tuple(float(p) for p in inst.operation.params)
        ops.append((name, qubits, params))  # type: ignore[arg-type]
    return ops


def build_qv_model_circuit(
    width: int,
    seed: int,
    *,
    depth: int | None = None,
):
    """Build one seeded QV model circuit of the given *width*.

    Args:
        width: Number of qubits ``m`` (>= 1).  The model-circuit depth
            defaults to ``m`` per the QV definition.
        seed: Base seed; per-trial circuits use ``seed + trial_index``.
        depth: Override the model depth (defaults to ``width``).

    Returns:
        A :class:`~uniqc.circuit_builder.Circuit` measuring all qubits in
        order (``c[i]`` = qubit ``i``).
    """
    if width < 1:
        raise ValueError(f"QV width must be >= 1, got {width}")
    depth = width if depth is None else depth
    if depth < 1:
        raise ValueError(f"QV depth must be >= 1, got {depth}")

    from uniqc.circuit_builder.qcircuit import Circuit

    rng = np.random.default_rng(seed)
    circuit = Circuit()
    for _layer in range(depth):
        permutation = rng.permutation(width)
        for pair_start in range(0, width - 1, 2):
            q0 = int(permutation[pair_start])
            q1 = int(permutation[pair_start + 1])
            _apply_su4_ops(circuit, q0, q1, haar_su4(rng))
    circuit.measure(*range(width))
    return circuit


def _apply_su4_ops(circuit, q0: int, q1: int, unitary: np.ndarray) -> None:
    """Append a decomposed SU(4) acting on absolute qubits (q0, q1)."""
    for name, qubits, params in _su4_to_ops(unitary):
        if name == "cx":
            control = q0 if qubits[0] == 0 else q1
            target = q0 if qubits[1] == 0 else q1
            circuit.cnot(control, target)
        else:
            target = q0 if qubits[0] == 0 else q1
            circuit.u3(target, *params)


def heavy_outputs_from_probabilities(probabilities: np.ndarray) -> frozenset[int]:
    """Return the heavy-output set of an ideal outcome distribution.

    Heavy outputs are the basis states with probability strictly above the
    median probability (Cross et al. 2019).  With an even-length distribution
    the median is the average of the two central order statistics.
    """
    probabilities = np.asarray(probabilities, dtype=float)
    if probabilities.size < 2:
        raise ValueError("Need at least two outcomes to define a median")
    if np.any(probabilities < 0) or not np.isclose(probabilities.sum(), 1.0, atol=1e-6):
        raise ValueError("Probabilities must be non-negative and normalized")
    median = float(np.median(probabilities))
    return frozenset(int(i) for i in np.nonzero(probabilities > median)[0])


@dataclasses.dataclass(frozen=True)
class QVTrialResult:
    """One QV trial (one model circuit executed once)."""

    trial: int
    seed: int
    width: int
    shots: int
    heavy_count: int
    h_obs: float
    sigma: float
    passed: bool


@dataclasses.dataclass(frozen=True)
class QVRunResult:
    """Aggregate result of a QV run over many trials at one width."""

    width: int
    depth: int
    trials: int
    shots: int
    base_seed: int
    backend: str
    mean_h: float
    sigma_mean: float
    trials_passed: int
    passed: bool
    quantum_volume: int | None
    trial_results: tuple[QVTrialResult, ...]

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "benchmark": "quantum_volume",
            "criterion": "Cross et al. 2019: trial h-2σ>2/3; run mean_h-2σ_mean>2/3; QV=2**width on success",
            "width": self.width,
            "depth": self.depth,
            "trials": self.trials,
            "shots": self.shots,
            "base_seed": self.base_seed,
            "backend": self.backend,
            "mean_heavy_output_probability": self.mean_h,
            "sigma_mean": self.sigma_mean,
            "trials_passed": self.trials_passed,
            "passed": self.passed,
            "quantum_volume": self.quantum_volume,
            "trial_results": [dataclasses.asdict(t) for t in self.trial_results],
        }


def _ideal_probabilities(circuit) -> np.ndarray:
    """Exact outcome probabilities of *circuit* via the local statevector simulator."""
    from uniqc.simulator import Simulator

    sim = Simulator(backend_type="statevector")
    probabilities = np.asarray(sim.simulate_pmeasure(circuit.originir), dtype=float)
    return probabilities


def _sample_shots(probabilities: np.ndarray, shots: int, seed: int) -> np.ndarray:
    """Multinomial shot sampling with an explicit seed."""
    rng = np.random.default_rng(seed)
    return rng.multinomial(shots, probabilities / probabilities.sum())


def _execute_on_dummy_backend(circuit, backend: str, shots: int, seed: int) -> np.ndarray:
    """Execute *circuit* on a dummy backend and return the sampled counts.

    Returns an array indexed by outcome integer over the measured qubits
    (local qubit ``i`` = bit ``i`` of the index, matching ``c[i]`` as LSB).
    """
    if backend != "dummy:local:simulator":
        raise ValueError(
            "The local QV entry supports 'dummy:local:simulator' only; "
            "real-device QV evidence requires a separate authorized cloud run."
        )
    # The dummy local simulator executes via the exact statevector path; to
    # keep honest per-shot statistics we sample with our own seeded RNG rather
    # than the probability-rounding convenience in UnifiedResult.
    return _sample_shots(_ideal_probabilities(circuit), shots, seed)


def run_quantum_volume(
    *,
    width: int,
    trials: int,
    shots: int = 1000,
    base_seed: int = 0,
    backend: str = "dummy:local:simulator",
) -> QVRunResult:
    """Run a seeded Quantum Volume benchmark at one width.

    Args:
        width: Model-circuit width ``m``; on success the credited quantum
            volume is ``2**m``.
        trials: Number of independent model circuits.
        shots: Shots per circuit (default 1000, the acceptance configuration).
        base_seed: Trial seeds are ``base_seed + trial``.
        backend: Local execution backend.  Only ``dummy:local:simulator`` is
            accepted in this entry — cloud QV runs are out of scope here.

    Returns:
        A :class:`QVRunResult` with per-trial evidence and the aggregate
        pass/fail judgement.
    """
    if trials < 1:
        raise ValueError(f"trials must be >= 1, got {trials}")
    if shots < 1:
        raise ValueError(f"shots must be >= 1, got {shots}")

    trial_results: list[QVTrialResult] = []
    for trial in range(trials):
        seed = base_seed + trial
        circuit = build_qv_model_circuit(width, seed)
        probabilities = _ideal_probabilities(circuit)
        heavy = heavy_outputs_from_probabilities(probabilities)
        counts = _execute_on_dummy_backend(circuit, backend, shots, seed + 1_000_000)
        heavy_count = int(sum(counts[outcome] for outcome in heavy))
        h_obs = heavy_count / shots
        sigma = float(np.sqrt(h_obs * (1.0 - h_obs) / shots))
        passed = h_obs - 2.0 * sigma > _HEAVY_THRESHOLD
        trial_results.append(
            QVTrialResult(
                trial=trial,
                seed=seed,
                width=width,
                shots=shots,
                heavy_count=heavy_count,
                h_obs=h_obs,
                sigma=sigma,
                passed=passed,
            )
        )

    mean_h = float(np.mean([t.h_obs for t in trial_results]))
    sigma_mean = float(np.sqrt(mean_h * (1.0 - mean_h) / (trials * shots)))
    run_passed = bool(mean_h - 2.0 * sigma_mean > _HEAVY_THRESHOLD)
    return QVRunResult(
        width=width,
        depth=width,
        trials=trials,
        shots=shots,
        base_seed=base_seed,
        backend=backend,
        mean_h=mean_h,
        sigma_mean=sigma_mean,
        trials_passed=sum(1 for t in trial_results if t.passed),
        passed=run_passed,
        quantum_volume=(1 << width) if run_passed else None,
        trial_results=tuple(trial_results),
    )
