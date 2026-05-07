"""Thermal state preparation circuit fragment."""

__all__ = ["thermal_state_circuit", "thermal_state_example"]

from typing import List, Optional
import math

from uniqc.circuit_builder import Circuit
from uniqc.algorithms._compat import dispatch_circuit_fragment


def _build_thermal_fragment(
    *,
    n_qubits: int,
    qubits: Optional[List[int]] = None,
    beta: float = 1.0,
) -> Circuit:
    if beta < 0:
        raise ValueError(f"beta must be non-negative, got {beta}")
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
    first_arg=None,
    beta: float = 1.0,
    qubits: Optional[List[int]] = None,
) -> Optional[Circuit]:
    r"""Build (or apply) a thermal-state preparation fragment for :math:`H=\sum_i Z_i`.

    Two calling conventions:

    .. code-block:: python

        # Fragment style (recommended):
        c = thermal_state_circuit(3, beta=1.0)         # returns Circuit

        # Legacy in-place style (deprecated):
        c = Circuit(3)
        thermal_state_circuit(c, beta=1.0)             # mutates c in place

    Each qubit is prepared in :math:`\sqrt{p_0}|0\rangle + \sqrt{p_1}|1\rangle`
    with :math:`p_0 = e^\beta / (e^\beta + e^{-\beta})`.

    Args:
        first_arg: Either ``n_qubits: int`` (fragment) or ``circuit: Circuit``
            (deprecated).
        beta: Inverse temperature (must be non-negative).
        qubits: Qubit indices to use.

    Returns:
        Fresh :class:`Circuit` in fragment mode; ``None`` in legacy mode.
    """
    return dispatch_circuit_fragment(
        name="thermal_state_circuit",
        fragment_builder=_build_thermal_fragment,
        first_arg=first_arg,
        legacy_qubits=qubits,
        extra_kwargs={"beta": beta},
    )


def thermal_state_example() -> Circuit:
    """Return a 3-qubit thermal-state circuit at :math:`\\beta=1` for tests/docs."""
    return thermal_state_circuit(3, beta=1.0)
