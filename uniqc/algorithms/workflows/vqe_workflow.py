"""Lightweight VQE workflow built on ansatz fragments + ``pauli_expectation``.

Unlike :mod:`uniqc.algorithms.core.training.vqe_torch`, this workflow does
**not** require ``torch`` or ``torchquantum``: it uses ``scipy.optimize`` for
the classical minimisation step and ``uniqc.simulator`` for the quantum part.

Use this when you want a zero-extras VQE driver. Use the torch-based version
when you want autodiff parameter-shift gradients and PyTorch interop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from uniqc.algorithms.core.ansatz.hea import hea
from uniqc.algorithms.core.measurement.pauli_expectation import pauli_expectation
from uniqc.circuit_builder import Circuit

__all__ = ["VQEResult", "run_vqe_workflow"]


@dataclass
class VQEResult:
    """Outcome of :func:`run_vqe_workflow`.

    Attributes:
        energy: Final (minimum) energy ⟨H⟩.
        params: Optimal ansatz parameters (numpy array).
        history: Per-iteration energies in evaluation order. Useful for
            convergence plots.
        n_iter: Number of objective evaluations.
        success: Whether the underlying scipy optimiser reported success.
        message: Optimiser termination message.
    """

    energy: float
    params: np.ndarray
    history: List[float] = field(default_factory=list)
    n_iter: int = 0
    success: bool = True
    message: str = ""


def _build_default_ansatz(n_qubits: int, depth: int) -> Callable[[np.ndarray], Circuit]:
    """Return ``params -> Circuit`` builder using the public HEA fragment."""

    def builder(params: np.ndarray) -> Circuit:
        c = hea(n_qubits=n_qubits, depth=depth, params=params)
        for q in range(n_qubits):
            c.measure(q)
        return c

    return builder


def _energy(circuit: Circuit, hamiltonian: Sequence[Tuple[str, float]],
            shots: Optional[int]) -> float:
    """Evaluate ⟨H⟩ = Σ_i c_i ⟨P_i⟩ by summing per-term Pauli expectations."""
    total = 0.0
    for pauli, coeff in hamiltonian:
        total += float(coeff) * pauli_expectation(circuit, pauli, shots=shots)
    return total


def run_vqe_workflow(
    hamiltonian: Sequence[Tuple[str, float]],
    *,
    n_qubits: Optional[int] = None,
    ansatz: Optional[Callable[[np.ndarray], Circuit]] = None,
    depth: int = 1,
    init_params: Optional[np.ndarray] = None,
    shots: Optional[int] = None,
    method: str = "COBYLA",
    options: Optional[dict] = None,
) -> VQEResult:
    """Run a scipy-driven VQE on ``hamiltonian``.

    Args:
        hamiltonian: Iterable of ``(pauli_string, coefficient)`` pairs.
            The Pauli string length must match ``n_qubits``.
        n_qubits: Number of qubits. Required when ``ansatz`` is ``None``;
            inferred from the first term's pauli length otherwise.
        ansatz: Optional ``params -> Circuit`` builder. If ``None`` the
            workflow uses a HEA with the requested ``depth`` and adds
            ``measure(q)`` on every qubit. The returned circuit must contain
            measurement instructions (``pauli_expectation`` requires them).
        depth: Layers in the default HEA ansatz. Ignored when ``ansatz``
            is supplied.
        init_params: Optional initial parameter vector. If ``None`` a small
            uniform random vector in ``[-π/8, π/8]`` is sampled. Length must
            match the ansatz's parameter count (``2 * n_qubits * depth`` for
            the default HEA).
        shots: Shots per Pauli-term expectation. ``None`` uses the analytic
            statevector estimator (recommended for early development).
        method: ``scipy.optimize.minimize`` method. ``COBYLA`` and ``Powell``
            are good gradient-free choices; switch to ``L-BFGS-B`` only when
            you supply a custom analytical gradient via ``options``.
        options: Optional dict forwarded to ``scipy.optimize.minimize``.
            Defaults to ``{"maxiter": 200, "rhobeg": 0.1}`` for COBYLA.

    Returns:
        :class:`VQEResult` with the minimum energy and parameters.

    Example:
        >>> # H = -1.0523 ZZ + 0.39793 ZI - 0.39793 IZ + 0.18093 XX
        >>> H = [("ZZ", -1.0523), ("ZI", 0.39793),
        ...      ("IZ", -0.39793), ("XX", 0.18093)]
        >>> result = run_vqe_workflow(H, n_qubits=2, depth=2)  # doctest: +SKIP
        >>> result.energy < -1.0                                # doctest: +SKIP
        True
    """
    from scipy.optimize import minimize

    hamiltonian = list(hamiltonian)
    if not hamiltonian:
        raise ValueError("hamiltonian must contain at least one (pauli, coeff) term")

    if n_qubits is None:
        if ansatz is not None:
            raise ValueError("n_qubits must be specified when passing a custom ansatz")
        n_qubits = len(hamiltonian[0][0])

    for pauli, _ in hamiltonian:
        if len(pauli) != n_qubits:
            raise ValueError(
                f"All Pauli terms must have length {n_qubits}, got {pauli!r}"
            )

    if ansatz is None:
        ansatz = _build_default_ansatz(n_qubits, depth)
        param_count = 2 * n_qubits * depth
    else:
        if init_params is None:
            raise ValueError(
                "init_params must be provided when supplying a custom ansatz "
                "(the workflow cannot infer the parameter count)."
            )
        param_count = len(init_params)

    if init_params is None:
        rng = np.random.default_rng(0)
        init_params = rng.uniform(-np.pi / 8, np.pi / 8, size=param_count)

    history: List[float] = []

    def objective(params: np.ndarray) -> float:
        circuit = ansatz(np.asarray(params))
        e = _energy(circuit, hamiltonian, shots)
        history.append(e)
        return e

    if options is None and method.upper() == "COBYLA":
        options = {"maxiter": 200, "rhobeg": 0.1}

    res = minimize(objective, np.asarray(init_params, dtype=float),
                   method=method, options=options)

    return VQEResult(
        energy=float(res.fun),
        params=np.asarray(res.x),
        history=history,
        n_iter=int(getattr(res, "nfev", len(history))),
        success=bool(res.success),
        message=str(res.message),
    )


def run_vqe_workflow_example() -> VQEResult:
    """Tiny H2-like 2-qubit Hamiltonian, used in tests/docs.

    Returns the :class:`VQEResult` from a cheap analytic-shot run.
    """
    h2_like = [
        ("ZZ", -1.0523),
        ("ZI", 0.39793),
        ("IZ", -0.39793),
        ("XX", 0.18093),
    ]
    return run_vqe_workflow(h2_like, n_qubits=2, depth=2, shots=None)
