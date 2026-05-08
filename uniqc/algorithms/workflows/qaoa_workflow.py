"""Lightweight QAOA workflow built on ``qaoa_ansatz`` + ``pauli_expectation``.

Mirrors :mod:`uniqc.algorithms.workflows.vqe_workflow`: scipy-based optimiser,
no torch / torchquantum dependency. The cost Hamiltonian is supplied as a list
of ``(pauli_string, coefficient)`` terms, identical to the VQE workflow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import numpy as np

from uniqc.algorithms.core.ansatz.qaoa_ansatz import qaoa_ansatz
from uniqc.algorithms.core.measurement.pauli_expectation import pauli_expectation
from uniqc.circuit_builder import Circuit

__all__ = ["QAOAResult", "run_qaoa_workflow"]


@dataclass
class QAOAResult:
    """Outcome of :func:`run_qaoa_workflow`.

    Attributes:
        energy: Minimum cost-function value ⟨H_C⟩ found.
        gammas: Optimal γ angles, length ``p``.
        betas:  Optimal β angles, length ``p``.
        history: Per-iteration energies (in evaluation order).
        n_iter: Number of objective evaluations.
        success: Whether the underlying scipy optimiser reported success.
        message: Optimiser termination message.
    """

    energy: float
    gammas: np.ndarray
    betas: np.ndarray
    history: List[float] = field(default_factory=list)
    n_iter: int = 0
    success: bool = True
    message: str = ""


def _energy(circuit: Circuit, hamiltonian: Sequence[Tuple[str, float]],
            shots: Optional[int]) -> float:
    total = 0.0
    for pauli, coeff in hamiltonian:
        total += float(coeff) * pauli_expectation(circuit, pauli, shots=shots)
    return total


def run_qaoa_workflow(
    cost_hamiltonian: Sequence[Tuple[str, float]],
    *,
    n_qubits: Optional[int] = None,
    p: int = 1,
    init_gammas: Optional[np.ndarray] = None,
    init_betas: Optional[np.ndarray] = None,
    shots: Optional[int] = None,
    method: str = "COBYLA",
    options: Optional[dict] = None,
) -> QAOAResult:
    """Run a scipy-driven QAOA on ``cost_hamiltonian``.

    Args:
        cost_hamiltonian: ``(pauli_string, coefficient)`` terms of H_C.
        n_qubits: Number of qubits. Inferred from the first Pauli term if
            ``None``.
        p: QAOA depth (number of γ/β layers).
        init_gammas: Optional initial γ vector of length ``p``. Defaults to
            a uniform-random vector in ``[0, π]``.
        init_betas:  Optional initial β vector of length ``p``. Defaults to
            a uniform-random vector in ``[0, π/2]``.
        shots: Shots per Pauli-term expectation. ``None`` uses the analytic
            statevector estimator.
        method: ``scipy.optimize.minimize`` method. Defaults to ``COBYLA``
            (gradient-free).
        options: Optional dict forwarded to ``scipy.optimize.minimize``.

    Returns:
        :class:`QAOAResult` with the optimised γ / β and minimum energy.

    Example:
        >>> # MaxCut on a 2-edge path graph 0-1-2:  H_C = (Z0Z1 + Z1Z2 - 2)/2
        >>> H = [("ZZI", 0.5), ("IZZ", 0.5), ("III", -1.0)]
        >>> result = run_qaoa_workflow(H, n_qubits=3, p=1)  # doctest: +SKIP
        >>> result.energy <= -0.5                            # doctest: +SKIP
        True
    """
    from scipy.optimize import minimize

    hamiltonian = list(cost_hamiltonian)
    if not hamiltonian:
        raise ValueError("cost_hamiltonian must contain at least one term")

    if n_qubits is None:
        n_qubits = len(hamiltonian[0][0])
    for pauli, _ in hamiltonian:
        if len(pauli) != n_qubits:
            raise ValueError(
                f"All Pauli terms must have length {n_qubits}, got {pauli!r}"
            )

    if p < 1:
        raise ValueError("p must be a positive integer")

    rng = np.random.default_rng(0)
    if init_gammas is None:
        init_gammas = rng.uniform(0.0, np.pi, size=p)
    if init_betas is None:
        init_betas = rng.uniform(0.0, np.pi / 2, size=p)
    if len(init_gammas) != p or len(init_betas) != p:
        raise ValueError(
            f"init_gammas / init_betas must have length p={p}"
        )

    history: List[float] = []

    def _to_indexed(pauli: str) -> str:
        """Convert 'ZZI' (positional) to 'Z0Z1' (qaoa_ansatz format)."""
        parts = []
        for i, ch in enumerate(pauli):
            if ch.upper() != "I":
                parts.append(f"{ch.upper()}{i}")
        return "".join(parts)

    # qaoa_ansatz needs the indexed form and skips constant (all-I) terms,
    # which only contribute a global phase. Pre-compute once.
    indexed_cost = []
    constant_offset = 0.0
    for pauli, coeff in hamiltonian:
        if all(ch.upper() == "I" for ch in pauli):
            constant_offset += float(coeff)
            continue
        indexed_cost.append((_to_indexed(pauli), float(coeff)))

    if not indexed_cost:
        raise ValueError(
            "cost_hamiltonian must contain at least one non-identity term"
        )

    def objective(packed: np.ndarray) -> float:
        gammas = packed[:p]
        betas = packed[p:]
        circuit = qaoa_ansatz(
            indexed_cost,
            p=p,
            gammas=gammas,
            betas=betas,
        )
        for q in range(n_qubits):
            circuit.measure(q)
        # _energy expects fixed-length ZZI form; use original hamiltonian
        # so the constant offset is included automatically (pauli_expectation
        # of all-I returns 1.0 by definition).
        e = _energy(circuit, hamiltonian, shots)
        history.append(e)
        return e

    x0 = np.concatenate([np.asarray(init_gammas, dtype=float),
                         np.asarray(init_betas, dtype=float)])

    if options is None and method.upper() == "COBYLA":
        options = {"maxiter": 200, "rhobeg": 0.1}

    res = minimize(objective, x0, method=method, options=options)

    g_opt = np.asarray(res.x[:p])
    b_opt = np.asarray(res.x[p:])
    return QAOAResult(
        energy=float(res.fun),
        gammas=g_opt,
        betas=b_opt,
        history=history,
        n_iter=int(getattr(res, "nfev", len(history))),
        success=bool(res.success),
        message=str(res.message),
    )


def run_qaoa_workflow_example() -> QAOAResult:
    """Smallest non-trivial example: 3-node path-graph MaxCut, p=1."""
    h_c = [("ZZI", 0.5), ("IZZ", 0.5), ("III", -1.0)]
    return run_qaoa_workflow(h_c, n_qubits=3, p=1, shots=None)
