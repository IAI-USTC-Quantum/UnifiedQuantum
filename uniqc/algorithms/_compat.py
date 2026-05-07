"""Internal helper: bridge legacy in-place algorithm APIs to the new
"circuit fragment" style.

The ``circuit-fragment`` design (see :doc:`/guide/algorithm_design`) requires
every public algorithm building block to **return a fresh** :class:`uniqc.circuit_builder.qcircuit.Circuit`
instead of mutating an input one. Many of UnifiedQuantum's existing
``*_circuit`` functions historically followed the older "first arg is a
Circuit, mutated in-place, returns ``None``" convention.

This module provides :func:`dispatch_circuit_fragment` which lets an API
support **both** signatures during the deprecation cycle:

- new style (recommended): ``qft_circuit(n_qubits, qubits=None, swaps=True) -> Circuit``
- legacy style: ``qft_circuit(circuit, qubits=..., swaps=...) -> None`` (mutates ``circuit`` in place,
  emits :class:`DeprecationWarning`)
"""

from __future__ import annotations

import warnings
from typing import Any, Callable, Optional

from uniqc.circuit_builder.qcircuit import Circuit


def dispatch_circuit_fragment(
    name: str,
    fragment_builder: Callable[..., Circuit],
    first_arg: Any,
    *,
    n_qubits_kwarg: str = "n_qubits",
    qubits_kwarg: str = "qubits",
    legacy_qubits: Optional[Any] = None,
    extra_kwargs: Optional[dict] = None,
) -> Optional[Circuit]:
    """Resolve the dual-mode signature for an algorithm fragment function.

    Args:
        name: The public name of the function (for warning messages).
        fragment_builder: A callable ``(n_qubits, qubits=None, **kw) -> Circuit``
            that constructs the fragment; it MUST return a fresh ``Circuit``.
        first_arg: The first positional argument supplied by the caller.
            If it is a :class:`Circuit`, legacy in-place mode is used. Otherwise
            it is interpreted as ``n_qubits``.
        n_qubits_kwarg: Name of the keyword to forward as the n_qubits arg.
        qubits_kwarg: Name of the keyword to forward as the qubits arg.
        legacy_qubits: When in legacy mode, the qubit indices to operate on
            inside the supplied circuit (``None`` = all qubits of the circuit).
        extra_kwargs: Extra keyword arguments to forward to ``fragment_builder``.

    Returns:
        ``None`` in legacy in-place mode (mutates the input circuit);
        a fresh :class:`Circuit` in fragment mode.
    """
    extra_kwargs = dict(extra_kwargs or {})

    if isinstance(first_arg, Circuit):
        warnings.warn(
            f"{name}(circuit, ...) (in-place form) is deprecated and will be "
            f"removed in a future release. Use the fragment form "
            f"`{name}(n_qubits, ...) -> Circuit` and merge with "
            f"`circuit.add_circuit(fragment)`.",
            DeprecationWarning,
            stacklevel=3,
        )
        target = first_arg
        qubits = legacy_qubits
        if qubits is None:
            qubits = list(range(target.qubit_num))
        n_qubits = (max(qubits) + 1) if qubits else 0
        kwargs = {qubits_kwarg: qubits, **extra_kwargs}
        kwargs[n_qubits_kwarg] = n_qubits
        fragment = fragment_builder(**kwargs)
        target.add_circuit(fragment)
        return None

    # New "fragment" style
    n_qubits = first_arg
    kwargs = {**extra_kwargs}
    if legacy_qubits is not None:
        kwargs[qubits_kwarg] = legacy_qubits
    if n_qubits is None:
        # Allow n_qubits to be inferred from qubits if provided
        qubits = kwargs.get(qubits_kwarg)
        if qubits is None:
            raise ValueError(
                f"{name}(...) requires either an integer n_qubits or a "
                f"non-empty qubits list."
            )
        n_qubits = max(qubits) + 1
    kwargs[n_qubits_kwarg] = n_qubits
    return fragment_builder(**kwargs)
