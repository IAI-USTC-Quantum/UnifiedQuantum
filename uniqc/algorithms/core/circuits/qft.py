"""Quantum Fourier Transform (QFT) circuit fragment.

This module follows the *circuit fragment* design (see
the design notes in the project README):

- ``qft_circuit(n_qubits, qubits=None, swaps=True) -> Circuit``
  is the canonical fragment-style API and returns a fresh
  :class:`uniqc.circuit_builder.qcircuit.Circuit`.
"""

__all__ = ["qft_circuit"]

import math

from uniqc._error_hints import format_enriched_message
from uniqc.circuit_builder import Circuit


def _build_qft_fragment(
    *,
    n_qubits: int,
    qubits: list[int] | None = None,
    swaps: bool = True,
) -> Circuit:
    """Pure fragment builder: returns a fresh ``Circuit`` containing QFT."""
    if qubits is None:
        qubits = list(range(n_qubits))

    n = len(qubits)
    if n < 1:
        raise ValueError(format_enriched_message("qft_circuit requires at least 1 qubit", "circuit_validation"))

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


def qft_circuit(
    n_qubits: int | None = None,
    qubits: list[int] | None = None,
    swaps: bool = True,
) -> Circuit:
    r"""Build a Quantum Fourier Transform fragment.

    .. code-block:: python

        qft = qft_circuit(n_qubits=3)              # returns a fresh Circuit
        qft = qft_circuit(3, qubits=[2, 3, 4])     # explicit qubit layout

    The QFT maps :math:`|j\rangle` to
    :math:`\frac{1}{\sqrt{N}} \sum_{k=0}^{N-1} e^{2\pi i jk / N} |k\rangle`.

    Args:
        n_qubits: Number of qubits. May be ``None`` if ``qubits`` is given,
            in which case it is inferred as ``max(qubits) + 1``.
        qubits: Qubit indices to operate on. ``None`` defaults to
            ``range(n_qubits)``.
        swaps: Whether to append the SWAP layer that reverses qubit order
            so the output follows the standard big-endian convention.

    Returns:
        A fresh :class:`Circuit` containing the QFT fragment.

    Raises:
        ValueError: Fewer than 1 qubit specified.
    """
    if n_qubits is None:
        if not qubits:
            raise ValueError("qft_circuit(...) requires either an integer n_qubits or a non-empty qubits list.")
        n_qubits = max(qubits) + 1
    return _build_qft_fragment(n_qubits=n_qubits, qubits=qubits, swaps=swaps)


def qft_example() -> Circuit:
    """Return a 3-qubit QFT circuit, used by docs and tests as a smoke example."""
    return qft_circuit(3)
