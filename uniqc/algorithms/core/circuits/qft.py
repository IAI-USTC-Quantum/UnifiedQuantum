"""Quantum Fourier Transform (QFT) circuit fragment.

This module follows the *circuit fragment* design (see
:doc:`/guide/algorithm_design`):

- ``qft_circuit(n_qubits, qubits=None, swaps=True) -> Circuit``
  is the canonical fragment-style API and returns a fresh
  :class:`uniqc.circuit_builder.qcircuit.Circuit`.
- ``qft_circuit(circuit, qubits=...)`` is kept as a deprecated in-place
  shim that emits :class:`DeprecationWarning`.
"""

__all__ = ["qft_circuit"]

from typing import List, Optional
import math

from uniqc.circuit_builder import Circuit
from uniqc.algorithms._compat import dispatch_circuit_fragment


def _build_qft_fragment(
    *,
    n_qubits: int,
    qubits: Optional[List[int]] = None,
    swaps: bool = True,
) -> Circuit:
    """Pure fragment builder: returns a fresh ``Circuit`` containing QFT."""
    if qubits is None:
        qubits = list(range(n_qubits))

    n = len(qubits)
    if n < 1:
        raise ValueError("qft_circuit requires at least 1 qubit")

    fragment = Circuit()
    for j in range(n):
        fragment.h(qubits[j])
        for k in range(j + 1, n):
            angle = math.pi / (2 ** (k - j))
            # Controlled-Rz emulated with CNOT decomposition
            fragment.rz(qubits[k], angle / 2)
            fragment.cnot(qubits[j], qubits[k])
            fragment.rz(qubits[k], -angle / 2)
            fragment.cnot(qubits[j], qubits[k])

    if swaps:
        for i in range(n // 2):
            fragment.swap(qubits[i], qubits[n - 1 - i])
    return fragment


def qft_circuit(first_arg=None, qubits: Optional[List[int]] = None, swaps: bool = True):
    r"""Build (or apply) a Quantum Fourier Transform fragment.

    Two calling conventions are supported:

    .. code-block:: python

        # Fragment style (recommended):
        qft = qft_circuit(n_qubits=3)              # returns a fresh Circuit
        qft = qft_circuit(3, qubits=[2, 3, 4])     # explicit qubit layout

        # Legacy in-place style (deprecated, emits DeprecationWarning):
        c = Circuit(3)
        qft_circuit(c, qubits=[0, 1, 2])           # mutates c, returns None

    The QFT maps :math:`|j\rangle` to
    :math:`\frac{1}{\sqrt{N}} \sum_{k=0}^{N-1} e^{2\pi i jk / N} |k\rangle`.

    Args:
        first_arg: Either an integer ``n_qubits`` (fragment mode) or a
            :class:`Circuit` (deprecated in-place mode). May be ``None`` if
            ``qubits`` is given.
        qubits: Qubit indices to operate on. ``None`` defaults to
            ``range(n_qubits)``.
        swaps: Whether to append the SWAP layer that reverses qubit order
            so the output follows the standard big-endian convention.

    Returns:
        A fresh :class:`Circuit` in fragment mode; ``None`` in legacy mode.

    Raises:
        ValueError: Fewer than 1 qubit specified.
    """
    return dispatch_circuit_fragment(
        name="qft_circuit",
        fragment_builder=_build_qft_fragment,
        first_arg=first_arg,
        legacy_qubits=qubits,
        extra_kwargs={"swaps": swaps},
    )


def qft_example() -> Circuit:
    """Return a 3-qubit QFT circuit, used by docs and tests as a smoke example."""
    return qft_circuit(3)

