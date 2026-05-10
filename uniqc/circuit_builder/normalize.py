"""Shared circuit input normalization.

This module provides the single source of truth for auto-detecting and
converting circuit input types (``uniqc.Circuit``, OriginIR strings,
OpenQASM 2.0 strings, and ``qiskit.QuantumCircuit``) into a unified
``uniqc.Circuit`` object.

The compile, simulator, and task-manager modules all delegate to these
functions so that every public entry point accepts the same set of input
types.
"""

from __future__ import annotations

__all__ = ["NormalizedCircuit", "normalize_circuit_input", "resolve_output_format"]

from dataclasses import dataclass
from typing import Any


@dataclass
class NormalizedCircuit:
    """Result of :func:`normalize_circuit_input`.

    Attributes
    ----------
    circuit : Circuit
        The unified :class:`uniqc.Circuit` object.
    original_format : str
        Detected input format: ``"circuit"``, ``"originir"``, ``"qasm"``,
        or ``"qiskit"``.
    original_input : Any
        The raw input value, retained so callers can round-trip
        (e.g. return a ``qiskit.QuantumCircuit`` when the user passed one).
    """

    circuit: Any  # Circuit (avoid hard import at module level)
    original_format: str
    original_input: Any = None


def normalize_circuit_input(circuit: Any) -> NormalizedCircuit:
    """Auto-detect input type and convert to :class:`uniqc.Circuit`.

    Accepted input types:

    - :class:`uniqc.Circuit` — returned as-is.
    - :class:`str` — parsed as OriginIR or OpenQASM 2.0 based on content
      heuristics (``QINIT`` → OriginIR, ``OPENQASM`` / ``qreg`` → QASM).
    - ``qiskit.QuantumCircuit`` — exported via ``qiskit.qasm2.dumps()``
      (or ``.qasm()`` for older Qiskit) then parsed.

    Not supported (by design): pyqpanda3 native types, Quark native APIs.

    Parameters
    ----------
    circuit : Any
        Circuit in any supported format.

    Returns
    -------
    NormalizedCircuit
        A dataclass containing the ``Circuit``, the detected format,
        and the original input.

    Raises
    ------
    TypeError
        If the input type is not recognized.
    CircuitTranslationError
        If parsing or conversion fails.
    """
    from .qcircuit import Circuit as _Circuit

    # 1. Already a Circuit
    if isinstance(circuit, _Circuit):
        return NormalizedCircuit(
            circuit=circuit,
            original_format="circuit",
            original_input=circuit,
        )

    # 2. String — auto-detect OriginIR vs QASM
    if isinstance(circuit, str):
        stripped = circuit.lstrip()
        if stripped.startswith("QINIT") or "\nCREG " in stripped[:200]:
            return NormalizedCircuit(
                circuit=_Circuit.from_originir(circuit),
                original_format="originir",
                original_input=circuit,
            )
        if stripped.startswith("OPENQASM") or "qreg " in stripped[:200] or "gate " in stripped[:200]:
            return NormalizedCircuit(
                circuit=_Circuit.from_qasm(circuit),
                original_format="qasm",
                original_input=circuit,
            )
        # Fallback: try OriginIR first (primary format), then QASM
        try:
            return NormalizedCircuit(
                circuit=_Circuit.from_originir(circuit),
                original_format="originir",
                original_input=circuit,
            )
        except Exception:
            pass
        try:
            return NormalizedCircuit(
                circuit=_Circuit.from_qasm(circuit),
                original_format="qasm",
                original_input=circuit,
            )
        except Exception:
            raise TypeError(
                f"Could not parse circuit string. Tried both OriginIR and "
                f"OpenQASM 2.0 formats. First 80 chars: {circuit[:80]!r}"
            ) from None

    # 3. qiskit.QuantumCircuit — lazy import
    try:
        from qiskit import QuantumCircuit as _QiskitQC

        if isinstance(circuit, _QiskitQC):
            try:
                from qiskit.qasm2 import dumps as _qasm2_dumps

                qasm_str = _qasm2_dumps(circuit)
            except ImportError:
                qasm_str = circuit.qasm()
            return NormalizedCircuit(
                circuit=_Circuit.from_qasm(qasm_str),
                original_format="qiskit",
                original_input=circuit,
            )
    except ImportError:
        pass

    raise TypeError(
        f"Unsupported circuit type: {type(circuit).__name__}. "
        f"Expected uniqc.Circuit, str (OriginIR/QASM), or qiskit.QuantumCircuit."
    )


def resolve_output_format(output_format: str, original_format: str) -> str:
    """Resolve the ``"auto"`` output-format sentinel.

    When ``output_format`` is ``"auto"``, the result matches
    ``original_format`` (with ``"qiskit"`` mapped to ``"circuit"`` since
    there is no native qiskit compile path).  Any explicit value is
    returned unchanged.

    Parameters
    ----------
    output_format : str
        One of ``"circuit"``, ``"originir"``, ``"qasm"``, or ``"auto"``.
    original_format : str
        The format detected by :func:`normalize_circuit_input`.

    Returns
    -------
    str
        The resolved format (one of ``"circuit"``, ``"originir"``, ``"qasm"``).
    """
    if output_format != "auto":
        return output_format
    # Map "qiskit" to "circuit" — there is no native qiskit output path.
    if original_format == "qiskit":
        return "circuit"
    return original_format
