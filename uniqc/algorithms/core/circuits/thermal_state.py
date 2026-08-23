"""Thermal state preparation circuit fragment."""

__all__ = ["thermal_state_circuit", "thermal_state_example"]

import math

from uniqc._error_hints import format_enriched_message
from uniqc.circuit_builder import Circuit


def _build_thermal_fragment(
    *,
    n_qubits: int,
    qubits: list[int] | None = None,
    beta: float = 1.0,
) -> Circuit:
    if beta < 0:
        raise ValueError(format_enriched_message(f"beta must be non-negative, got {beta}", "circuit_validation"))
    if qubits is None:
        qubits = list(range(n_qubits))
    exp_beta = math.exp(beta)
    exp_neg_beta = math.exp(-beta)
    p0 = exp_beta / (exp_beta + exp_neg_beta)
    theta = 2.0 * math.acos(math.sqrt(p0))
    fragment = Circuit()
    for q in qubits:
        fragment.ry(q, theta)
    return fragment


def thermal_state_circuit(
    n_qubits: int | None = None,
    beta: float = 1.0,
    qubits: list[int] | None = None,
) -> Circuit:
    r"""Build a thermal-state preparation fragment for :math:`H=\sum_i Z_i`.

    .. code-block:: python

        c = thermal_state_circuit(3, beta=1.0)         # returns Circuit

    Each qubit is prepared in :math:`\sqrt{p_0}|0\rangle + \sqrt{p_1}|1\rangle`
    with :math:`p_0 = e^\beta / (e^\beta + e^{-\beta})`.

    Args:
        n_qubits: Number of qubits. May be ``None`` if ``qubits`` is given,
            in which case it is inferred as ``max(qubits) + 1``.
        beta: Inverse temperature (must be non-negative).
        qubits: Qubit indices to use.

    Returns:
        A fresh :class:`Circuit` containing the preparation fragment.
    """
    if n_qubits is None:
        if not qubits:
            raise ValueError(
                "thermal_state_circuit(...) requires either an integer n_qubits or a non-empty qubits list."
            )
        n_qubits = max(qubits) + 1
    return _build_thermal_fragment(n_qubits=n_qubits, qubits=qubits, beta=beta)


def thermal_state_example() -> Circuit:
    """Return a 3-qubit thermal-state circuit at :math:`\\beta=1` for tests/docs."""
    return thermal_state_circuit(3, beta=1.0)
