"""Circuit normalisation utilities.

Provides the :data:`AnyQuantumCircuit` type alias and the
:func:`normalize_to_circuit` helper used by public APIs (``submit_task``,
simulators, ``compile``) to accept heterogeneous circuit representations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from .qcircuit import Circuit

__all__ = ["AnyQuantumCircuit", "normalize_to_circuit"]

#: Accepted input types for circuit-oriented APIs.
#: A :class:`~uniqc.circuit_builder.Circuit` object, an OriginIR string,
#: or an OpenQASM 2.0 string.
AnyQuantumCircuit = Union["Circuit", str]


def normalize_to_circuit(input: AnyQuantumCircuit) -> "Circuit":
    """Convert *AnyQuantumCircuit* to a :class:`Circuit` object.

    Accepted inputs:

    - A :class:`Circuit` instance (returned as-is).
    - An OriginIR string (tried first).
    - An OpenQASM 2.0 string (fallback).

    Raises:
        TypeError: If *input* is not a ``Circuit`` or ``str``.
        ValueError: If the string cannot be parsed as either OriginIR or QASM.
    """
    from .qcircuit import Circuit

    if isinstance(input, Circuit):
        return input

    if not isinstance(input, str):
        raise TypeError(
            f"Expected Circuit, originir string, or qasm string, "
            f"got {type(input).__name__}"
        )

    # Try OriginIR first.
    from uniqc.compile.originir import OriginIR_BaseParser

    parser = OriginIR_BaseParser()
    try:
        parser.parse(input)
        return parser.to_circuit()
    except Exception:
        pass

    # Fall back to QASM.
    from uniqc.compile.qasm import OpenQASM2_BaseParser

    qasm_parser = OpenQASM2_BaseParser()
    qasm_parser.parse(input)
    return qasm_parser.to_circuit()
