"""Entangled state preparation circuits: GHZ, W, and Cluster states.

All three follow the *circuit fragment* design (see
the design notes in the project README). The canonical APIs are:

- ``ghz_state_circuit(n_qubits, qubits=None) -> Circuit``
- ``w_state_circuit(n_qubits, qubits=None) -> Circuit``
- ``cluster_state_circuit(n_qubits, qubits=None, edges=None) -> Circuit``

The shorter names ``ghz_state``, ``w_state`` and ``cluster_state`` are
fragment-style aliases: pass an integer ``n_qubits`` to get a fresh fragment.
"""

__all__ = [
    "ghz_state",
    "w_state",
    "cluster_state",
    "ghz_state_circuit",
    "w_state_circuit",
    "cluster_state_circuit",
]


from uniqc._error_hints import format_enriched_message
from uniqc.algorithms.core.circuits.dicke_state import _build_dicke_fragment
from uniqc.circuit_builder import Circuit


def _infer_n_qubits(name: str, n_qubits: int | None, qubits: list[int] | None) -> int:
    """Infer ``n_qubits`` from a qubits list when not given explicitly."""
    if n_qubits is None:
        if not qubits:
            raise ValueError(f"{name}(...) requires either an integer n_qubits or a non-empty qubits list.")
        n_qubits = max(qubits) + 1
    return n_qubits


def _build_ghz_fragment(*, n_qubits: int, qubits: list[int] | None = None) -> Circuit:
    if qubits is None:
        qubits = list(range(n_qubits))
    if len(qubits) < 2:
        raise ValueError(format_enriched_message("ghz_state requires at least 2 qubits", "circuit_validation"))
    fragment = Circuit()
    fragment.h(qubits[0])
    for i in range(len(qubits) - 1):
        fragment.cnot(qubits[i], qubits[i + 1])
    return fragment


def ghz_state(n_qubits: int | None = None, qubits: list[int] | None = None) -> Circuit:
    r"""Prepare a GHZ state :math:`(|0\ldots0\rangle + |1\ldots1\rangle)/\sqrt 2`.

    .. code-block:: python

        c = ghz_state(3)                         # returns Circuit
        c = ghz_state(3, qubits=[1, 2, 4])       # use offset qubits

    Args:
        n_qubits: Number of qubits. May be ``None`` if ``qubits`` is given,
            in which case it is inferred as ``max(qubits) + 1``.
        qubits: Qubit indices.

    Returns:
        A fresh :class:`Circuit` containing the preparation fragment.
    """
    n_qubits = _infer_n_qubits("ghz_state", n_qubits, qubits)
    return _build_ghz_fragment(n_qubits=n_qubits, qubits=qubits)


def ghz_state_circuit(n_qubits: int, qubits: list[int] | None = None) -> Circuit:
    """Fragment-style alias of :func:`ghz_state` (always returns a fresh ``Circuit``)."""
    return _build_ghz_fragment(n_qubits=n_qubits, qubits=qubits)


def _build_w_fragment(*, n_qubits: int, qubits: list[int] | None = None) -> Circuit:
    if qubits is None:
        qubits = list(range(n_qubits))
    if len(qubits) < 2:
        raise ValueError(format_enriched_message("w_state requires at least 2 qubits", "circuit_validation"))
    # A W state is the k=1 Dicke state.
    return _build_dicke_fragment(n_qubits=n_qubits, qubits=qubits, k=1)


def w_state(n_qubits: int | None = None, qubits: list[int] | None = None) -> Circuit:
    r"""Prepare a W state — equal superposition of single-excitation basis states.

    See :func:`ghz_state` for the signature contract.
    """
    n_qubits = _infer_n_qubits("w_state", n_qubits, qubits)
    return _build_w_fragment(n_qubits=n_qubits, qubits=qubits)


def w_state_circuit(n_qubits: int, qubits: list[int] | None = None) -> Circuit:
    """Fragment-style alias of :func:`w_state`."""
    return _build_w_fragment(n_qubits=n_qubits, qubits=qubits)


def _build_cluster_fragment(
    *,
    n_qubits: int,
    qubits: list[int] | None = None,
    edges: list[tuple[int, int]] | None = None,
) -> Circuit:
    if qubits is None:
        qubits = list(range(n_qubits))
    n = len(qubits)
    if n < 1:
        raise ValueError(format_enriched_message("cluster_state requires at least 1 qubit", "circuit_validation"))
    fragment = Circuit()
    for q in qubits:
        fragment.h(q)
    if edges is None:
        edges = [(i, i + 1) for i in range(n - 1)]
    for src_idx, tgt_idx in edges:
        if src_idx >= n or tgt_idx >= n:
            raise ValueError(
                format_enriched_message(
                    f"Edge ({src_idx}, {tgt_idx}) out of range for {n} qubits", "circuit_validation"
                )
            )
        fragment.cz(qubits[src_idx], qubits[tgt_idx])
    return fragment


def cluster_state(
    n_qubits: int | None = None,
    qubits: list[int] | None = None,
    edges: list[tuple[int, int]] | None = None,
) -> Circuit:
    r"""Prepare a cluster (graph) state via :math:`H^{\otimes n}` + CZ on each edge.

    See :func:`ghz_state` for the signature contract. ``edges``
    defaults to a linear nearest-neighbour chain.
    """
    n_qubits = _infer_n_qubits("cluster_state", n_qubits, qubits)
    return _build_cluster_fragment(n_qubits=n_qubits, qubits=qubits, edges=edges)


def cluster_state_circuit(
    n_qubits: int,
    qubits: list[int] | None = None,
    edges: list[tuple[int, int]] | None = None,
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
