"""Unified quantum circuit simulator.

Provides ``Simulator`` and ``NoisySimulator`` — the public simulator classes
that accept *any* quantum-circuit representation (``Circuit`` object, OriginIR
string, or OpenQASM 2.0 string) and auto-detect the input format at runtime.

Key exports:
    - Simulator: Ideal simulator (statevector / density matrix backends).
    - NoisySimulator: Noisy simulator with error-model injection.
"""

__all__ = ["Simulator", "NoisySimulator"]

from typing import Dict, List

from .base_simulator import BaseNoisySimulator, BaseSimulator
from .error_model import ErrorLoader
from .opcode_simulator import OpcodeSimulator
from uniqc.compile.originir.originir_base_parser import OriginIR_BaseParser
from uniqc.compile.qasm.qasm_base_parser import OpenQASM2_BaseParser


def _to_originir_str(quantum_code):
    """Normalise *AnyQuantumCircuit* to an OriginIR or QASM string.

    Accepts a ``Circuit`` object (calls ``.originir``), an OriginIR string, or
    a QASM string.  Raises ``TypeError`` for unsupported types.
    """
    from uniqc.circuit_builder.qcircuit import Circuit as _Circuit

    if isinstance(quantum_code, _Circuit):
        return quantum_code.originir
    if isinstance(quantum_code, str):
        return quantum_code
    raise TypeError(
        f"Expected Circuit, originir string, or qasm string, "
        f"got {type(quantum_code).__name__}"
    )


class Simulator(BaseSimulator):
    """Unified ideal quantum circuit simulator.

    Accepts any of the following as *quantum_code*:

    - A :class:`~uniqc.circuit_builder.Circuit` object
    - An OriginIR string (``circuit.originir``)
    - An OpenQASM 2.0 string (``circuit.qasm``)

    The input format is detected automatically: OriginIR is tried first, and
    if parsing fails the code falls back to QASM.

    Args:
        backend_type: Backend type (``"statevector"`` or ``"densitymatrix"``).
        available_qubits: List of available qubit indices (optional).
        available_topology: List of available qubit pairs (optional).
        **extra_kwargs: Additional arguments passed to
            :class:`BaseSimulator` (e.g. ``least_qubit_remapping``).
    """

    def __init__(
        self,
        backend_type="statevector",
        available_qubits: List[int] = None,
        available_topology: List[List[int]] = None,
        **extra_kwargs,
    ):
        super().__init__(
            backend_type, available_qubits, available_topology, **extra_kwargs
        )
        self.parser = OriginIR_BaseParser()

    # ------------------------------------------------------------------
    # simulate_preprocess — auto-detect input format
    # ------------------------------------------------------------------

    def simulate_preprocess(self, quantum_code):
        """Parse and preprocess a quantum program.

        *quantum_code* may be a :class:`Circuit`, an OriginIR string, or a
        QASM string.  The format is detected automatically.

        Returns:
            Tuple of (processed_program_body, measurement_qubits).
        """
        quantum_code = _to_originir_str(quantum_code)

        # Try OriginIR first.
        self._clear()
        self.parser = OriginIR_BaseParser()
        try:
            self.parser.parse(quantum_code)
        except Exception:
            # Fall back to QASM.
            self._clear()
            self.parser = OpenQASM2_BaseParser()
            self.parser.parse(quantum_code)

        self._extract_actual_used_qubits()

        if self.available_qubits or self.available_topology:
            self._check_available_qubits()

        processed_program_body = self._process_program_body()
        processed_measure_qubits = self._process_measure_qubits()

        return processed_program_body, processed_measure_qubits

    def _clear(self):
        super()._clear()
        self.parser = OriginIR_BaseParser()


class NoisySimulator(BaseNoisySimulator):
    """Unified noisy quantum circuit simulator.

    Same input flexibility as :class:`Simulator` (``Circuit``, OriginIR, or
    QASM string), with additional support for gate-level error injection and
    readout-error modelling.

    Args:
        backend_type: Backend type (must be ``"density_matrix"`` for noise).
        available_qubits: List of available qubit indices (optional).
        available_topology: List of available qubit pairs (optional).
        error_loader: :class:`ErrorLoader` instance for gate error injection.
        readout_error: Dict mapping qubit index to ``[p01, p10]`` readout
            error rates.
    """

    def __init__(
        self,
        backend_type="statevector",
        available_qubits: List[int] = None,
        available_topology: List[List[int]] = None,
        error_loader: ErrorLoader = None,
        readout_error: Dict[int, List[float]] = {},
    ):
        super().__init__(
            backend_type,
            available_qubits,
            available_topology,
            error_loader,
            readout_error,
        )
        self.parser = OriginIR_BaseParser()

    def simulate_preprocess(self, quantum_code):
        """Parse, preprocess, and inject errors into a quantum program.

        *quantum_code* may be a :class:`Circuit`, an OriginIR string, or a
        QASM string.

        Returns:
            Tuple of (error-injected program_body, measurement_qubits).
        """
        quantum_code = _to_originir_str(quantum_code)

        # Try OriginIR first.
        self._clear()
        self.parser = OriginIR_BaseParser()
        try:
            self.parser.parse(quantum_code)
        except Exception:
            self._clear()
            self.parser = OpenQASM2_BaseParser()
            self.parser.parse(quantum_code)

        self._extract_actual_used_qubits()

        if self.available_qubits or self.available_topology:
            self._check_available_qubits()

        processed_program_body = self._process_program_body()
        processed_measure_qubits = self._process_measure_qubits()

        # Apply error injection (same logic as BaseNoisySimulator).
        if self.error_loader:
            self.error_loader.process_opcodes(processed_program_body)
            processed_program_body = self.error_loader.opcodes

        return processed_program_body, processed_measure_qubits

    def _clear(self):
        super()._clear()
        self.parser = OriginIR_BaseParser()
