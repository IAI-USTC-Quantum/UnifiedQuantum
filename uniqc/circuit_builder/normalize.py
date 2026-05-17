"""Shared circuit input normalization.

Provides the :data:`AnyQuantumCircuit` type alias and
:func:`normalize_circuit_input` used by compile, simulators, and task-manager
modules so that every public entry point accepts the same set of input types.
"""

from __future__ import annotations

__all__ = [
    "AnyQuantumCircuit",
    "NormalizedCircuit",
    "normalize_circuit_input",
    "normalize_to_circuit",
    "resolve_output_format",
]

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Union

if TYPE_CHECKING:
    from .qcircuit import Circuit

#: Accepted input types for circuit-oriented APIs.
#: A :class:`~uniqc.circuit_builder.Circuit` object, an OriginIR string,
#: or an OpenQASM 2.0 string.
AnyQuantumCircuit = Union["Circuit", str]


@dataclass
class NormalizedCircuit:
    """Result of :func:`normalize_circuit_input`.

    Attributes
    ----------
    circuit : Circuit
        The unified :class:`uniqc.Circuit` object.
    type : str
        Detected input format: ``"circuit"``, ``"originir"``, ``"qasm"``,
        or ``"qiskit"``.
    original_input : Any
        The raw input value, retained so callers can round-trip.
    """

    circuit: Any
    type: str
    original_input: Any = None


def _parse_originir(text: str):
    from uniqc.compile.originir import OriginIR_BaseParser

    parser = OriginIR_BaseParser()
    parser.parse(text)
    return parser.to_circuit()


def _parse_qasm(text: str):
    from uniqc.compile.qasm import OpenQASM2_BaseParser

    parser = OpenQASM2_BaseParser()
    parser.parse(text)
    return parser.to_circuit()


def normalize_circuit_input(circuit) -> NormalizedCircuit:
    """Auto-detect input type and convert to :class:`uniqc.Circuit`.

    Accepted input types:

    - :class:`uniqc.Circuit` — returned as-is.
    - :class:`str` — parsed as OriginIR or OpenQASM 2.0.
    - ``qiskit.QuantumCircuit`` — exported via ``qiskit.qasm2.dumps()`` then parsed.
    - ``pyqpanda3.QProg`` — converted via OriginIR round-trip.

    Parameters
    ----------
    circuit : Any
        Circuit in any supported format.

    Returns
    -------
    NormalizedCircuit
        Dataclass with ``.circuit``, ``.type``, and ``.original_input`` fields.
    """
    from .qcircuit import Circuit

    if isinstance(circuit, Circuit):
        return NormalizedCircuit(circuit=circuit, type="circuit", original_input=circuit)

    if isinstance(circuit, str):
        stripped = circuit.lstrip()
        if stripped.upper().startswith(("OPENQASM", "QREG", "CREG", "MEASURE")):
            try:
                return NormalizedCircuit(circuit=_parse_qasm(circuit), type="qasm", original_input=circuit)
            except Exception:
                pass
        try:
            return NormalizedCircuit(circuit=_parse_originir(circuit), type="originir", original_input=circuit)
        except Exception:
            pass
        # Last-ditch QASM attempt
        return NormalizedCircuit(circuit=_parse_qasm(circuit), type="qasm", original_input=circuit)

    # qiskit.QuantumCircuit
    try:
        import qiskit.qasm2

        qasm_str = qiskit.qasm2.dumps(circuit)
        return NormalizedCircuit(circuit=_parse_qasm(qasm_str), type="qiskit", original_input=circuit)
    except Exception:
        pass

    # pyqpanda3.QProg
    try:
        import pyqpanda3

        if isinstance(circuit, pyqpanda3.QProg):
            originir_str = pyqpanda3.convert_qprog_to_originir(circuit)
            return NormalizedCircuit(
                circuit=_parse_originir(originir_str),
                type="originir",
                original_input=circuit,
            )
    except Exception:
        pass

    raise TypeError(
        f"Cannot normalize input of type {type(circuit).__name__}. "
        f"Expected Circuit, originir string, qasm string, "
        f"qiskit.QuantumCircuit, or pyqpanda3.QProg."
    )


def normalize_to_circuit(input: AnyQuantumCircuit) -> Circuit:
    """Convert *AnyQuantumCircuit* to a :class:`Circuit` object."""
    return normalize_circuit_input(input).circuit


def resolve_output_format(output_format: str, type: str) -> str:
    """Resolve the output format string to a canonical name.

    Parameters
    ----------
    output_format : str
        User-specified format: ``"originir"``, ``"qasm"``, ``"circuit"``, or
        ``"auto"``. ``"auto"`` returns the same format as the input *type*.
    type : str
        Detected input format from :func:`normalize_circuit_input`.

    Returns
    -------
    str
        Canonical format: ``"originir"`` or ``"qasm"``.
    """
    if output_format == "auto":
        return "originir" if type in ("circuit", "originir") else "qasm"
    return output_format
