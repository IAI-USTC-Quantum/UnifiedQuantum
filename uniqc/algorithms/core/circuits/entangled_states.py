"""Entangled state preparation circuits: GHZ, W, and Cluster states.

All three follow the *circuit fragment* design (see
:doc:`/guide/algorithm_design`). The canonical APIs are:

- ``ghz_state_circuit(n_qubits, qubits=None) -> Circuit``
- ``w_state_circuit(n_qubits, qubits=None) -> Circuit``
- ``cluster_state_circuit(n_qubits, qubits=None, edges=None) -> Circuit``

The shorter names ``ghz_state``, ``w_state`` and ``cluster_state`` are
preserved as dual-mode dispatchers: pass an integer to get a fresh fragment;
pass an existing ``Circuit`` (deprecated) to mutate it in place.
"""

__all__ = [
    "ghz_state",
    "w_state",
    "cluster_state",
    "ghz_state_circuit",
    "w_state_circuit",
    "cluster_state_circuit",
]

from typing import List, Optional, Tuple

from uniqc.circuit_builder import Circuit
from uniqc.algorithms._compat import dispatch_circuit_fragment
from uniqc.algorithms.core.circuits.dicke_state import dicke_state_circuit


def _build_ghz_fragment(*, n_qubits: int, qubits: Optional[List[int]] = None) -> Circuit:
    if qubits is None:
        qubits = list(range(n_qubits))
    if len(qubits) < 2:
        raise ValueError("ghz_state requires at least 2 qubits")
    fragment = Circuit()
    fragment.h(qubits[0])
    for i in range(len(qubits) - 1):
        fragment.cnot(qubits[i], qubits[i + 1])
    return fragment


def ghz_state(first_arg=None, qubits: Optional[List[int]] = None):
    r"""Prepare a GHZ state :math:`(|0\ldots0\rangle + |1\ldots1\rangle)/\sqrt 2`.

    Two calling conventions:

    .. code-block:: python

        # Fragment style (recommended):
        c = ghz_state(3)                         # returns Circuit
        c = ghz_state(3, qubits=[1, 2, 4])       # use offset qubits

        # Legacy in-place style (deprecated):
        c = Circuit(3)
        ghz_state(c)                             # mutates c in place

    Args:
        first_arg: Either an integer ``n_qubits`` (fragment mode) or a
            :class:`Circuit` (deprecated in-place mode).
        qubits: Qubit indices.

    Returns:
        A fresh :class:`Circuit` in fragment mode; ``None`` in legacy mode.
    """
    return dispatch_circuit_fragment(
        name="ghz_state",
        fragment_builder=_build_ghz_fragment,
        first_arg=first_arg,
        legacy_qubits=qubits,
    )


def ghz_state_circuit(n_qubits: int, qubits: Optional[List[int]] = None) -> Circuit:
    """Fragment-style alias of :func:`ghz_state` (always returns a fresh ``Circuit``)."""
    return _build_ghz_fragment(n_qubits=n_qubits, qubits=qubits)


def _build_w_fragment(*, n_qubits: int, qubits: Optional[List[int]] = None) -> Circuit:
    if qubits is None:
        qubits = list(range(n_qubits))
    if len(qubits) < 2:
        raise ValueError("w_state requires at least 2 qubits")
    # Build a fresh circuit and use the (already-fragment-style)
    # ``dicke_state_circuit`` to populate it with k=1.
    fragment = Circuit()
    dicke_state_circuit(fragment, k=1, qubits=qubits)  # legacy in-place; safe on fragment
    return fragment


def w_state(first_arg=None, qubits: Optional[List[int]] = None):
    r"""Prepare a W state — equal superposition of single-excitation basis states.

    See :func:`ghz_state` for the dual-mode signature contract.
    """
    return dispatch_circuit_fragment(
        name="w_state",
        fragment_builder=_build_w_fragment,
        first_arg=first_arg,
        legacy_qubits=qubits,
    )


def w_state_circuit(n_qubits: int, qubits: Optional[List[int]] = None) -> Circuit:
    """Fragment-style alias of :func:`w_state`."""
    return _build_w_fragment(n_qubits=n_qubits, qubits=qubits)


def _build_cluster_fragment(
    *,
    n_qubits: int,
    qubits: Optional[List[int]] = None,
    edges: Optional[List[Tuple[int, int]]] = None,
) -> Circuit:
    if qubits is None:
        qubits = list(range(n_qubits))
    n = len(qubits)
    if n < 1:
        raise ValueError("cluster_state requires at least 1 qubit")
    fragment = Circuit()
    for q in qubits:
        fragment.h(q)
    if edges is None:
        edges = [(i, i + 1) for i in range(n - 1)]
    for src_idx, tgt_idx in edges:
        if src_idx >= n or tgt_idx >= n:
            raise ValueError(
                f"Edge ({src_idx}, {tgt_idx}) out of range for {n} qubits"
            )
        fragment.cz(qubits[src_idx], qubits[tgt_idx])
    return fragment


def cluster_state(
    first_arg=None,
    qubits: Optional[List[int]] = None,
    edges: Optional[List[Tuple[int, int]]] = None,
):
    r"""Prepare a cluster (graph) state via :math:`H^{\otimes n}` + CZ on each edge.

    See :func:`ghz_state` for the dual-mode signature contract. ``edges``
    defaults to a linear nearest-neighbour chain.
    """
    return dispatch_circuit_fragment(
        name="cluster_state",
        fragment_builder=_build_cluster_fragment,
        first_arg=first_arg,
        legacy_qubits=qubits,
        extra_kwargs={"edges": edges},
    )


def cluster_state_circuit(
    n_qubits: int,
    qubits: Optional[List[int]] = None,
    edges: Optional[List[Tuple[int, int]]] = None,
) -> Circuit:
    """Fragment-style alias of :func:`cluster_state`."""
    return _build_cluster_fragment(n_qubits=n_qubits, qubits=qubits, edges=edges)


def entangled_states_example() -> dict:
    """Return a dict ``{ 'ghz': Circuit, 'w': Circuit, 'cluster': Circuit }`` for tests/docs."""
    return {
        "ghz": ghz_state_circuit(3),
        "w": w_state_circuit(3),
        "cluster": cluster_state_circuit(4),
    }
