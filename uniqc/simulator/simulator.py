"""Unified quantum circuit simulator.

This module provides a single ``Simulator`` class that auto-detects the input
format (OriginIR, OpenQASM 2.0, or ``uniqc.Circuit``) and delegates to the
appropriate parser.  ``NoisySimulator`` extends it with noise-model support.

Key exports:
    - Simulator: Ideal simulator for any supported circuit format.
    - NoisySimulator: Noisy simulator with error-model injection.
"""

from __future__ import annotations

from typing import Dict, List, TYPE_CHECKING

from .base_simulator import BaseNoisySimulator, BaseSimulator
from .error_model import ErrorLoader

if TYPE_CHECKING:
    from .uniqc_cpp import *

__all__ = ["Simulator", "NoisySimulator"]


class Simulator(BaseSimulator):
    """Unified quantum circuit simulator.

    Accepts any supported input format and auto-detects the parser:

    * :class:`uniqc.Circuit` — opcodes are read directly (parser bypassed).
    * ``str`` — OriginIR or OpenQASM 2.0 (detected from content heuristics).
    * ``qiskit.QuantumCircuit`` / other external types — normalized to
      ``Circuit`` via :func:`uniqc.circuit_builder.normalize.normalize_circuit_input`.

    See :data:`uniqc.circuit_builder.AnyQuantumCircuit` for the full list of
    accepted input types.

    Args:
        backend_type: Backend type (``"statevector"`` or ``"densitymatrix"``).
        available_qubits: List of available qubit indices (optional).
        available_topology: List of available qubit pairs (optional).
        **extra_kwargs: Additional arguments passed to
            :class:`BaseSimulator` (e.g. ``least_qubit_remapping``).
    """

    def __init__(
        self,
        backend_type: str = "statevector",
        available_qubits: List[int] | None = None,
        available_topology: List[List[int]] | None = None,
        **extra_kwargs,
    ):
        super().__init__(
            backend_type, available_qubits, available_topology, **extra_kwargs
        )
        self.parser = None
        self._raw_source: str | None = None
        self._splitted_lines: list[str] | None = None

    # ------------------------------------------------------------------
    # Parser selection
    # ------------------------------------------------------------------

    def _select_parser(self, source: str):
        """Return the appropriate parser for *source* based on content."""
        stripped = source.lstrip()
        if stripped.upper().startswith(("OPENQASM", "QREG")):
            from uniqc.compile.qasm import OpenQASM2_BaseParser

            return OpenQASM2_BaseParser()
        # Default to OriginIR (primary format).
        from uniqc.compile.originir.originir_base_parser import (
            OriginIR_BaseParser,
        )

        return OriginIR_BaseParser()

    # ------------------------------------------------------------------
    # Preprocessing
    # ------------------------------------------------------------------

    def simulate_preprocess(self, input_data):
        """Parse and preprocess any supported circuit input.

        Returns:
            Tuple of ``(processed_program_body, measure_qubit)``.
        """
        from uniqc.circuit_builder.qcircuit import Circuit as _Circuit
        from uniqc.circuit_builder.normalize import normalize_circuit_input

        self._clear()

        # Circuit objects: direct opcode path (no parser).
        if isinstance(input_data, _Circuit):
            return self._simulate_from_circuit(input_data)

        # Non-string, non-Circuit (e.g. qiskit.QuantumCircuit): normalize.
        if not isinstance(input_data, str):
            result = normalize_circuit_input(input_data)
            return self._simulate_from_circuit(result.circuit)

        # String path: auto-detect parser from content.
        self._raw_source = input_data
        self.parser = self._select_parser(input_data)
        self.parser.parse(input_data)
        self._splitted_lines = input_data.splitlines()

        self._extract_actual_used_qubits()
        if self.available_qubits or self.available_topology:
            self._check_available_qubits()

        processed_program_body = self._process_program_body()
        measure_qubit = self._process_measure()

        measure_qubit_cbit = sorted(measure_qubit, key=lambda k: k[1])
        measure_qubit = [q for q, _ in measure_qubit_cbit]
        return processed_program_body, measure_qubit

    # ------------------------------------------------------------------
    # Program body processing (topology validation with line numbers)
    # ------------------------------------------------------------------

    def _process_program_body(self):
        """Process opcodes with topology validation.

        Both OriginIR and QASM parsers already exclude ``MEASURE`` from
        ``program_body`` and store them in ``parser.measure_qubits``.
        When ``self._splitted_lines`` is available the error messages
        include the offending source line.
        """
        processed: list = []
        program_body = self.parser.program_body
        splitted = self._splitted_lines

        for i, opcode in enumerate(program_body):
            (
                operation,
                qubit,
                cbit,
                parameter,
                dagger_flag,
                control_qubits_set,
            ) = opcode

            if isinstance(qubit, list) and self.available_topology:
                if len(qubit) > 2:
                    msg = (
                        "Real chip does not support gate of 3-qubit or more. "
                        "The dummy server does not support either. "
                        "You should consider decomposite it."
                    )
                    if splitted and i + 2 < len(splitted):
                        msg += f"\nLine {i + 2} ({splitted[i + 2]})."
                    raise ValueError(msg)
                if (
                    [int(qubit[0]), int(qubit[1])] not in self.available_topology
                    and [int(qubit[1]), int(qubit[0])]
                    not in self.available_topology
                ):
                    msg = "Unsupported topology."
                    if splitted and i + 2 < len(splitted):
                        msg += f"\nLine {i + 2} ({splitted[i + 2]})."
                    raise ValueError(msg)

            if qubit is not None:
                if isinstance(qubit, list):
                    mapped_qubit = [self.qubit_mapping[q] for q in qubit]
                else:
                    mapped_qubit = self.qubit_mapping[qubit]

            processed.append(
                (
                    operation,
                    mapped_qubit,
                    cbit,
                    parameter,
                    dagger_flag,
                    control_qubits_set,
                )
            )
        return processed

    # ------------------------------------------------------------------
    # State reset
    # ------------------------------------------------------------------

    def _clear(self):
        super()._clear()
        self.parser = None
        self._raw_source = None
        self._splitted_lines = None


class NoisySimulator(Simulator, BaseNoisySimulator):
    """Noisy unified quantum circuit simulator.

    Same input-format auto-detection as :class:`Simulator`, with
    noise-model injection via :class:`ErrorLoader`.

    Args:
        backend_type: Backend type (``"statevector"`` or ``"densitymatrix"``).
        available_qubits: List of available qubit indices (optional).
        available_topology: List of available qubit pairs (optional).
        error_loader: ErrorLoader instance for gate error injection (optional).
        readout_error: Dict mapping qubit index to ``[p0, p1]`` readout error
            rates (optional).
    """

    def __init__(
        self,
        backend_type: str = "statevector",
        available_qubits: List[int] | None = None,
        available_topology: List[List[int]] | None = None,
        error_loader: ErrorLoader | None = None,
        readout_error: Dict[int, List[float]] | None = None,
    ):
        if readout_error is None:
            readout_error = {}
        BaseNoisySimulator.__init__(
            self,
            backend_type,
            available_qubits,
            available_topology,
            error_loader,
            readout_error,
        )
        self.parser = None
        self._raw_source: str | None = None
        self._splitted_lines: list[str] | None = None

    def simulate_preprocess(self, input_data):
        """Parse, preprocess, and inject errors into the circuit.

        Delegates to :meth:`Simulator.simulate_preprocess` for format
        auto-detection and preprocessing, then applies noise injection
        from :class:`BaseNoisySimulator`.
        """
        processed_program_body, measure_qubit = Simulator.simulate_preprocess(
            self, input_data
        )
        if self.error_loader:
            self.error_loader.process_opcodes(processed_program_body)
            processed_program_body = self.error_loader.opcodes
        return processed_program_body, measure_qubit
