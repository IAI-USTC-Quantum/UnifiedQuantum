"""High-level classical-shadow workflow.

Wraps :func:`uniqc.algorithms.core.measurement.classical_shadow.classical_shadow`
and :func:`shadow_expectation` so that the user can request multiple Pauli
expectations from a single shadow dataset in one call.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence

import numpy as np

from uniqc.algorithms.core.measurement.classical_shadow import (
    classical_shadow,
    shadow_expectation,
    ShadowSnapshot,
)
from uniqc.circuit_builder import Circuit

__all__ = ["ShadowWorkflowResult", "run_classical_shadow_workflow"]


@dataclass
class ShadowWorkflowResult:
    """Outcome of :func:`run_classical_shadow_workflow`.

    Attributes:
        snapshots: List of :class:`ShadowSnapshot` produced by the shadow run.
        expectations: Mapping ``pauli_string -> estimated <P>``.
        n_snapshots: Number of shadow snapshots collected (= ``shots``).
    """

    snapshots: List[ShadowSnapshot]
    expectations: Dict[str, float] = field(default_factory=dict)
    n_snapshots: int = 0


def run_classical_shadow_workflow(
    circuit: Circuit,
    pauli_observables: Sequence[str],
    *,
    shots: int = 1000,
    n_shadow: int | None = None,
    qubits: list[int] | None = None,
) -> ShadowWorkflowResult:
    """Collect a classical-shadow dataset and estimate multiple observables.

    Args:
        circuit: Quantum circuit. Must contain measurements on every qubit
            that participates in any of ``pauli_observables``.
        pauli_observables: Pauli strings to estimate. All must have the same
            length and that length must equal the circuit's qubit count.
        shots: Shots per snapshot forwarded to ``classical_shadow``.
        n_shadow: Optional number of distinct snapshots forwarded to
            ``classical_shadow``. ``None`` defaults to that function's
            built-in default.
        qubits: Optional qubit subset forwarded to ``classical_shadow``.

    Returns:
        :class:`ShadowWorkflowResult` with both the raw snapshots and the
        per-observable estimates.

    Example:
        >>> from uniqc.circuit_builder import Circuit
        >>> from uniqc.algorithms.workflows import classical_shadow_workflow as csw
        >>> c = Circuit(); c.h(0); c.cx(0, 1); c.measure(0); c.measure(1)
        >>> r = csw.run_classical_shadow_workflow(
        ...     c, ["ZZ", "XX"], shots=500
        ... )                                                    # doctest: +SKIP
        >>> abs(r.expectations["ZZ"] - 1.0) < 0.5                # doctest: +SKIP
        True
    """
    if not pauli_observables:
        raise ValueError("pauli_observables must contain at least one Pauli string")

    lengths = {len(p) for p in pauli_observables}
    if len(lengths) != 1:
        raise ValueError(
            f"All Pauli observables must have the same length, got: "
            f"{sorted(lengths)}"
        )

    kwargs: dict = {"shots": shots}
    if n_shadow is not None:
        kwargs["n_shadow"] = n_shadow
    if qubits is not None:
        kwargs["qubits"] = qubits

    snapshots = classical_shadow(circuit, **kwargs)
    expectations: Dict[str, float] = {}
    for pauli in pauli_observables:
        expectations[pauli] = float(shadow_expectation(snapshots, pauli))

    return ShadowWorkflowResult(
        snapshots=snapshots,
        expectations=expectations,
        n_snapshots=len(snapshots),
    )


def run_classical_shadow_workflow_example() -> ShadowWorkflowResult:
    """Bell-state shadow estimation for ZZ and XX observables."""
    c = Circuit()
    c.h(0)
    c.cx(0, 1)
    c.measure(0)
    c.measure(1)
    return run_classical_shadow_workflow(c, ["ZZ", "XX"], shots=500)
