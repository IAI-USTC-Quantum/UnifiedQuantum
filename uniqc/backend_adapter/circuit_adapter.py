"""Circuit adapter layer for converting UnifiedQuantum circuits to provider-native formats.

This module provides adapter classes for converting UnifiedQuantum Circuit objects
to native circuit formats used by different quantum computing platforms:
- OriginQ (pyqpanda)
- QuarkStudio (OpenQASM 2.0)
- IBM (qiskit)
- TianYan (QCIS text, via cqlib)
- LogicalQubit (lqcloud QuantumCircuit)

Usage::

    from uniqc.backend_adapter.circuit_adapter import OriginQCircuitAdapter, QuarkCircuitAdapter, IBMCircuitAdapter
    from uniqc.circuit_builder import Circuit

    # Create a UnifiedQuantum circuit
    circuit = Circuit()
    circuit.h(0)
    circuit.cnot(0, 1)
    circuit.measure(0, 1)

    # Convert to provider-native circuits
    originq_adapter = OriginQCircuitAdapter()
    pyqpanda_circuit = originq_adapter.adapt(circuit)

    quark_adapter = QuarkCircuitAdapter()
    qasm2 = quark_adapter.adapt(circuit)

    ibm_adapter = IBMCircuitAdapter()
    qiskit_circuit = ibm_adapter.adapt(circuit)
"""

from __future__ import annotations

__all__ = [
    "CircuitAdapter",
    "OriginQCircuitAdapter",
    "QuarkCircuitAdapter",
    "IBMCircuitAdapter",
    "TianyanCircuitAdapter",
    "LogicalQubitCircuitAdapter",
    "originir_to_qcis",
    "originir_to_lqcloud_circuit",
]

import abc
from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    from uniqc.circuit_builder.qcircuit import Circuit

# Type variable for provider-native circuit types
T = TypeVar("T")


class CircuitAdapter(abc.ABC, Generic[T]):
    """Abstract base class for circuit adapters.

    Provides a unified interface for converting UnifiedQuantum Circuit
    objects to provider-native circuit formats.
    """

    @abc.abstractmethod
    def adapt(self, circuit: Circuit) -> T:
        """Convert a UnifiedQuantum Circuit to the provider's native circuit format.

        Args:
            circuit: UnifiedQuantum Circuit object.

        Returns:
            Provider-native circuit object.
        """
        ...

    def adapt_batch(self, circuits: list[Circuit]) -> list[T]:
        """Convert multiple UnifiedQuantum Circuits to provider-native format.

        Args:
            circuits: List of UnifiedQuantum Circuit objects.

        Returns:
            List of provider-native circuit objects.
        """
        return [self.adapt(c) for c in circuits]

    @abc.abstractmethod
    def get_supported_gates(self) -> list[str]:
        """Return the list of gate names supported by this adapter.

        Returns:
            List of supported gate names (uppercase strings).
        """
        ...

    def _get_originir(self, circuit: Circuit) -> str:
        """Extract OriginIR string from a UnifiedQuantum Circuit.

        Args:
            circuit: UnifiedQuantum Circuit object.

        Returns:
            OriginIR string representation of the circuit.
        """
        return circuit.originir


class OriginQCircuitAdapter(CircuitAdapter[Any]):
    """Adapter for converting UnifiedQuantum Circuit to pyqpanda (OriginQ) format.

    Uses pyqpanda3's intermediate compiler to convert OriginIR to QProg.
    """

    # Gate mapping from OriginIR names to pyqpanda supported gates
    SUPPORTED_GATES = [
        "H",
        "X",
        "Y",
        "Z",
        "S",
        "T",
        "SX",
        "RX",
        "RY",
        "RZ",
        "RPhi",
        "RPhi90",
        "RPhi180",
        "U1",
        "U2",
        "U3",
        "U4",
        "CNOT",
        "CZ",
        "SWAP",
        "ISWAP",
        "TOFFOLI",
        "CSWAP",
        "XX",
        "YY",
        "ZZ",
        "XY",
        "PHASE2Q",
        "UU15",
        "I",
        "BARRIER",
        "MEASURE",
    ]

    def __init__(self) -> None:
        self._pyqpanda3: Any = None
        self._convert_originir: Any = None

    def _ensure_imports(self) -> None:
        """Lazily import pyqpanda3 modules."""
        if self._pyqpanda3 is None or self._convert_originir is None:
            try:
                from pyqpanda3 import core as pyqpanda3_core
                from pyqpanda3.intermediate_compiler import (
                    convert_originir_string_to_qprog,
                )

                self._pyqpanda3 = pyqpanda3_core
                self._convert_originir = convert_originir_string_to_qprog
            except ImportError as e:
                raise RuntimeError(
                    "pyqpanda3 is required for OriginQCircuitAdapter. Install it with: pip install pyqpanda3"
                ) from e

    def adapt(self, circuit: Circuit) -> str:
        """Convert UnifiedQuantum Circuit to OriginIR string.

        The OriginQAdapter.submit() receives this string and converts it
        to QProg internally via translate_circuit(). Returning QProg here
        would cause submit() to double-convert, breaking translate_circuit().

        Args:
            circuit: UnifiedQuantum Circuit object.

        Returns:
            OriginIR format string.
        """
        return self._get_originir(circuit)

    def get_supported_gates(self) -> list[str]:
        """Return the list of gate names supported by this adapter."""
        return self.SUPPORTED_GATES.copy()


class QuarkCircuitAdapter(CircuitAdapter[str]):
    """Adapter for converting UnifiedQuantum Circuit to OpenQASM 2.0 for QuarkStudio.

    QuarkStudio's interface accepts an OpenQASM 2.0 string in the
    task dictionary, so this adapter intentionally returns text rather than a
    provider-specific circuit object.
    """

    SUPPORTED_GATES = [
        "H",
        "X",
        "Y",
        "Z",
        "S",
        "T",
        "SX",
        "RX",
        "RY",
        "RZ",
        "U1",
        "U2",
        "U3",
        "CNOT",
        "CX",
        "CZ",
        "SWAP",
        "ISWAP",
        "TOFFOLI",
        "CCX",
        "CSWAP",
        "MEASURE",
        "BARRIER",
        "I",
        "ID",
    ]

    def adapt(self, circuit: Circuit) -> str:
        """Convert UnifiedQuantum Circuit to OpenQASM 2.0 text."""
        return circuit.qasm

    def get_supported_gates(self) -> list[str]:
        """Return the list of gate names supported by this adapter."""
        return self.SUPPORTED_GATES.copy()


class IBMCircuitAdapter(CircuitAdapter[Any]):
    """Adapter for converting UnifiedQuantum Circuit to qiskit (IBM) format.

    Converts Circuit -> OriginIR -> QASM -> Qiskit QuantumCircuit.
    """

    # QASM 2.0 standard gates supported by qiskit
    SUPPORTED_GATES = [
        "H",
        "X",
        "Y",
        "Z",
        "S",
        "T",
        "SX",
        "RX",
        "RY",
        "RZ",
        "U1",
        "U2",
        "U3",
        "CNOT",
        "CX",
        "CZ",
        "SWAP",
        "ISWAP",
        "TOFFOLI",
        "CCX",
        "CSWAP",
        "Fredkin",
        "MEASURE",
        "BARRIER",
        "I",
        "ID",
    ]

    def __init__(self) -> None:
        self._qiskit: Any = None

    def _ensure_imports(self) -> None:
        """Lazily import qiskit modules."""
        if self._qiskit is None:
            try:
                import qiskit

                self._qiskit = qiskit
            except ImportError as e:
                raise RuntimeError(
                    "qiskit is required for IBMCircuitAdapter. Install it with: pip install qiskit"
                ) from e

    def adapt(self, circuit: Circuit) -> Any:
        """Convert UnifiedQuantum Circuit to qiskit QuantumCircuit.

        The conversion path is:
        UnifiedQuantum Circuit -> OriginIR -> QASM -> Qiskit QuantumCircuit

        Args:
            circuit: UnifiedQuantum Circuit object.

        Returns:
            qiskit.QuantumCircuit object.
        """
        self._ensure_imports()

        # Get QASM representation (via OriginIR -> QASM conversion)
        qasm_str = circuit.qasm

        # Parse QASM to Qiskit QuantumCircuit
        return self._qiskit.QuantumCircuit.from_qasm_str(qasm_str)

    def adapt_with_transpilation(
        self,
        circuit: Circuit,
        backend: Any = None,
        optimization_level: int = 1,
        **kwargs: Any,
    ) -> Any:
        """Convert and transpile the circuit for a specific backend.

        Args:
            circuit: UnifiedQuantum Circuit object.
            backend: Qiskit backend to transpile for.
            optimization_level: Transpiler optimization level (0-3).
            **kwargs: Additional arguments for qiskit.compiler.transpile.

        Returns:
            Transpiled qiskit.QuantumCircuit object.
        """
        self._ensure_imports()
        qiskit_circuit = self.adapt(circuit)

        if backend is not None:
            return self._qiskit.compiler.transpile(
                qiskit_circuit, backend=backend, optimization_level=optimization_level, **kwargs
            )

        return qiskit_circuit

    def get_supported_gates(self) -> list[str]:
        """Return the list of gate names supported by this adapter."""
        return self.SUPPORTED_GATES.copy()


# -----------------------------------------------------------------------------
# TianYan (天衍) — OriginIR -> QCIS text
# -----------------------------------------------------------------------------


def _format_gate_angle(parameter: Any, gate: str, *, dagger: bool = False) -> str:
    """Render a numeric gate angle for a text IR; reject symbolic parameters."""
    try:
        value = float(parameter)
    except (TypeError, ValueError) as exc:
        raise NotImplementedError(
            f"Gate '{gate}' has a non-numeric parameter ({parameter!r}); "
            "cloud platforms require concrete numeric angles."
        ) from exc
    if dagger:
        value = -value
    return repr(value)


def _parse_originir_line(line: str) -> tuple[Any, ...]:
    """Parse one OriginIR line, raising a clear error on failure."""
    from uniqc.compile.originir.originir_line_parser import OriginIR_LineParser

    try:
        return OriginIR_LineParser.parse_line(line)
    except Exception as exc:
        raise ValueError(f"Cannot parse OriginIR line {line!r}: {exc}") from exc


def _reject_control_flow(operation: str | None, control_qubits: Any, line: str, target: str) -> None:
    """Reject OriginIR control-flow constructs the target IR cannot express."""
    if operation in ("CONTROL", "ENDCONTROL", "DAGGER", "ENDDAGGER"):
        raise NotImplementedError(
            f"OriginIR {operation} blocks are not supported by the {target} adapter; "
            f"use inline 'dagger' suffixes on S/T/SX or rotation gates instead ({line!r})."
        )
    if control_qubits:
        raise NotImplementedError(
            f"controlled_by(...) is not supported by the {target} adapter ({line!r})."
        )


def originir_to_qcis(originir: str) -> str:
    """Convert an OriginIR string to QCIS text for the TianYan platform.

    QCIS is a line-based format, e.g. ``H Q0``, ``RX Q0 0.12``,
    ``CZ Q0 Q6``, ``M Q0``. Measurement lines carry no classical-bit
    index — the measurement order *is* the cbit order, so ``MEASURE``
    lines must assign cbits sequentially (the uniqc convention).

    Args:
        originir: Circuit in OriginIR format.

    Returns:
        QCIS text (one instruction per line).

    Raises:
        ValueError: If a line cannot be parsed or a qubit index is out of
            range for the ``QINIT`` size.
        NotImplementedError: If the circuit uses a gate or construct with
            no QCIS equivalent.
    """
    lines: list[str] = []
    n_qubits: int | None = None
    n_measures = 0

    def _q(index: int) -> str:
        if n_qubits is None:
            raise ValueError("QINIT must appear before any gate operation.")
        if not 0 <= index < n_qubits:
            raise ValueError(f"Qubit index q[{index}] is out of range for QINIT {n_qubits}.")
        return f"Q{index}"

    for raw_line in originir.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        operation, qubit, cbit, parameter, dagger_flag, control_qubits = _parse_originir_line(line)

        if operation == "QINIT":
            n_qubits = int(qubit)
            continue
        if operation == "CREG":
            continue

        _reject_control_flow(operation, control_qubits, line, "TianYan QCIS")

        if operation == "MEASURE":
            if cbit is not None and int(cbit) != n_measures:
                raise NotImplementedError(
                    f"QCIS records measurements in order; MEASURE must assign cbits "
                    f"sequentially (expected c[{n_measures}], got c[{cbit}] in {line!r})."
                )
            lines.append(f"M {_q(int(qubit))}")
            n_measures += 1
            continue
        if operation == "BARRIER":
            # QCIS has no barrier instruction; barriers carry no semantics
            # for cloud sampling, so they are dropped.
            continue

        if operation in ("H", "X", "Y", "Z"):
            # Self-inverse: dagger is a no-op.
            lines.append(f"{operation} {_q(int(qubit))}")
        elif operation == "S":
            lines.append(f"{'SD' if dagger_flag else 'S'} {_q(int(qubit))}")
        elif operation == "T":
            lines.append(f"{'TD' if dagger_flag else 'T'} {_q(int(qubit))}")
        elif operation == "SX":
            lines.append(f"{'X2M' if dagger_flag else 'X2P'} {_q(int(qubit))}")
        elif operation in ("RX", "RY", "RZ"):
            angle = _format_gate_angle(parameter, operation, dagger=bool(dagger_flag))
            lines.append(f"{operation} {_q(int(qubit))} {angle}")
        elif operation == "CNOT":
            lines.append(f"CX {_q(int(qubit[0]))} {_q(int(qubit[1]))}")
        elif operation == "CZ":
            lines.append(f"CZ {_q(int(qubit[0]))} {_q(int(qubit[1]))}")
        elif operation == "SWAP":
            lines.append(f"SWAP {_q(int(qubit[0]))} {_q(int(qubit[1]))}")
        elif operation == "XY":
            angle = _format_gate_angle(parameter, operation, dagger=bool(dagger_flag))
            lines.append(f"XY {_q(int(qubit[0]))} {_q(int(qubit[1]))} {angle}")
        elif operation == "TOFFOLI":
            lines.append(f"CCX {_q(int(qubit[0]))} {_q(int(qubit[1]))} {_q(int(qubit[2]))}")
        else:
            raise NotImplementedError(
                f"Gate '{operation}' is not supported by the TianYan QCIS adapter. "
                f"Supported gates: {TianyanCircuitAdapter.SUPPORTED_GATES}"
            )

    if n_qubits is None:
        raise ValueError("OriginIR is missing the QINIT header.")
    return "\n".join(lines)


def originir_to_lqcloud_circuit(originir: str, circuit_cls: Any) -> Any:
    """Convert an OriginIR string to an lqcloud ``QuantumCircuit``.

    Gate methods follow qiskit conventions: parameterised gates take the
    angle first (``rx(theta, qubit)``), measurements take
    ``measure(qubit, clbit)``.

    Args:
        originir: Circuit in OriginIR format.
        circuit_cls: The ``lqcloud.QuantumCircuit`` class (passed in so
            this function never imports lqcloud itself).

    Returns:
        An lqcloud QuantumCircuit object.

    Raises:
        ValueError: If a line cannot be parsed.
        NotImplementedError: If the circuit uses a gate or construct with
            no lqcloud equivalent.
    """
    n_qubits: int | None = None
    n_cbits: int | None = None
    for raw_line in originir.splitlines():
        line = raw_line.strip()
        if line.startswith("QINIT"):
            n_qubits = int(line.split()[1])
        elif line.startswith("CREG"):
            n_cbits = int(line.split()[1])
    if n_qubits is None:
        raise ValueError("OriginIR is missing the QINIT header.")

    qc = circuit_cls(n_qubits, n_cbits if n_cbits is not None else n_qubits)
    n_measures = 0

    for raw_line in originir.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        operation, qubit, cbit, parameter, dagger_flag, control_qubits = _parse_originir_line(line)

        if operation in ("QINIT", "CREG"):
            continue

        _reject_control_flow(operation, control_qubits, line, "LogicalQubit")

        if operation == "MEASURE":
            qc.measure(int(qubit), int(cbit) if cbit is not None else n_measures)
            n_measures += 1
            continue
        if operation == "BARRIER":
            qc.barrier()
            continue

        if operation in ("H", "X", "Y", "Z"):
            # Self-inverse: dagger is a no-op.
            getattr(qc, operation.lower())(int(qubit))
        elif operation == "I":
            qc.id(int(qubit))
        elif operation == "S":
            (qc.sdg if dagger_flag else qc.s)(int(qubit))
        elif operation == "T":
            (qc.tdg if dagger_flag else qc.t)(int(qubit))
        elif operation == "SX":
            (qc.sxdg if dagger_flag else qc.sx)(int(qubit))
        elif operation in ("RX", "RY", "RZ"):
            angle = float(_format_gate_angle(parameter, operation, dagger=bool(dagger_flag)))
            getattr(qc, operation.lower())(angle, int(qubit))
        elif operation == "U1":
            angle = float(_format_gate_angle(parameter, operation, dagger=bool(dagger_flag)))
            qc.p(angle, int(qubit))
        elif operation == "CNOT":
            qc.cx(int(qubit[0]), int(qubit[1]))
        elif operation == "CZ":
            qc.cz(int(qubit[0]), int(qubit[1]))
        elif operation == "SWAP":
            qc.swap(int(qubit[0]), int(qubit[1]))
        elif operation == "ISWAP":
            qc.iswap(int(qubit[0]), int(qubit[1]))
        elif operation == "TOFFOLI":
            qc.ccx(int(qubit[0]), int(qubit[1]), int(qubit[2]))
        else:
            raise NotImplementedError(
                f"Gate '{operation}' is not supported by the LogicalQubit adapter. "
                f"Supported gates: {LogicalQubitCircuitAdapter.SUPPORTED_GATES}"
            )

    return qc


class TianyanCircuitAdapter(CircuitAdapter[str]):
    """Adapter for converting UnifiedQuantum Circuit to QCIS text (TianYan).

    Returns the QCIS string; :class:`TianyanAdapter` submits it via
    ``cqlib.TianYanPlatform.submit_job``.
    """

    # OriginIR gate names accepted by originir_to_qcis().
    SUPPORTED_GATES = [
        "H",
        "X",
        "Y",
        "Z",
        "S",
        "T",
        "SX",
        "RX",
        "RY",
        "RZ",
        "CNOT",
        "CZ",
        "SWAP",
        "XY",
        "TOFFOLI",
        "MEASURE",
        "BARRIER",
    ]

    def adapt(self, circuit: Circuit) -> str:
        """Convert UnifiedQuantum Circuit to QCIS text."""
        return originir_to_qcis(self._get_originir(circuit))

    def get_supported_gates(self) -> list[str]:
        """Return the list of gate names supported by this adapter."""
        return self.SUPPORTED_GATES.copy()


class LogicalQubitCircuitAdapter(CircuitAdapter[Any]):
    """Adapter for converting UnifiedQuantum Circuit to an lqcloud QuantumCircuit."""

    # OriginIR gate names accepted by originir_to_lqcloud_circuit().
    SUPPORTED_GATES = [
        "H",
        "X",
        "Y",
        "Z",
        "S",
        "T",
        "SX",
        "I",
        "RX",
        "RY",
        "RZ",
        "U1",
        "CNOT",
        "CZ",
        "SWAP",
        "ISWAP",
        "TOFFOLI",
        "MEASURE",
        "BARRIER",
    ]

    def __init__(self) -> None:
        self._QuantumCircuit: Any = None

    def _ensure_imports(self) -> None:
        """Lazily import lqcloud."""
        if self._QuantumCircuit is None:
            from uniqc.backend_adapter.task.optional_deps import require

            lqcloud = require("lqcloud", "logicalqubit")
            self._QuantumCircuit = lqcloud.QuantumCircuit

    def adapt(self, circuit: Circuit) -> Any:
        """Convert UnifiedQuantum Circuit to an lqcloud QuantumCircuit."""
        self._ensure_imports()
        return originir_to_lqcloud_circuit(self._get_originir(circuit), self._QuantumCircuit)

    def get_supported_gates(self) -> list[str]:
        """Return the list of gate names supported by this adapter."""
        return self.SUPPORTED_GATES.copy()
