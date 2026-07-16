"""Higher-level simulator for dynamic OriginIR-ext programs.

:class:`OriginIR_ext_Simulator` sits above
:class:`~uniqc.simulator.opcode_simulator.OpcodeSimulator` and interprets the
*non-opcode* control flow (``QIF``/``QWHILE``) of a classical / control-flow
program tree, driving the OpcodeSimulator — which owns the CREG store — for the
linear opcodes (gates, ``MEASURE`` → CREG, ``RESET``, and the classical
instructions ``AND``/``OR``/``XOR``/``MOV``/``NOT``).

Because mid-circuit measurement + classical feedback make each run stochastic,
results are produced by **per-shot re-execution**: every shot runs the whole
program from a fresh ``|0...0>`` state and reads the final CREG bitstring
(``c[0]`` = LSB). The exact aggregate paths (``simulate_pmeasure`` /
``simulate_stateprob``) are therefore ill-defined and raise.
"""

from __future__ import annotations

__all__ = ["OriginIR_ext_Simulator", "LoopWatchdogError"]

import numpy as np

from uniqc.circuit_builder.classical_program import (
    ClassicalOp,
    GateOp,
    IfBlock,
    MeasureOp,
    ResetOp,
    WhileBlock,
)

from .base_simulator import BaseSimulator


class LoopWatchdogError(RuntimeError):
    """Raised when a ``QWHILE`` loop exceeds its configured ``max_iterations``."""


class OriginIR_ext_Simulator(BaseSimulator):
    """Interpreter for dynamic OriginIR-ext programs (CREG + control flow).

    Accepts a :class:`~uniqc.circuit_builder.qcircuit.Circuit` (with or without
    a structured ``dynamic_program``) or an OriginIR-ext string. Ordinary flat
    circuits are executed as a single linear opcode sequence followed by their
    terminal measurements.

    Args:
        backend_type: ``"statevector"`` or ``"density_matrix"`` (see
            :func:`uniqc.simulator.opcode_simulator.backend_alias`).
        available_qubits: Optional list of available qubit indices.
        available_topology: Optional list of available qubit pairs.
        seed: Optional RNG seed (applied once before a shot loop / single run)
            for deterministic mid-circuit measurement outcomes.
        max_while_iterations: Optional global override of every ``QWHILE``
            block's internal iteration watchdog. ``None`` honours each block's
            own ``max_iterations``.
    """

    def __init__(
        self,
        backend_type="statevector",
        available_qubits: list[int] = None,
        available_topology: list[list[int]] = None,
        seed: int | None = None,
        max_while_iterations: int | None = None,
        **extra_kwargs,
    ):
        super().__init__(backend_type, available_qubits, available_topology, **extra_kwargs)
        self.seed = seed
        self.max_while_iterations = max_while_iterations

    # ------------------------------------------------------------------
    # Input normalization
    # ------------------------------------------------------------------

    def _resolve_program(self, quantum_code):
        """Normalise *quantum_code* to ``(nodes, qubit_num, cbit_num, qrams)``."""
        from uniqc.circuit_builder.qcircuit import Circuit

        if isinstance(quantum_code, str):
            circuit = Circuit.from_originir(quantum_code)
        elif isinstance(quantum_code, Circuit):
            circuit = quantum_code
        else:
            raise TypeError(f"Expected a Circuit or OriginIR-ext string, got {type(quantum_code).__name__}.")

        circuit.check_dynamic_program_closed()

        if circuit.dynamic_program is not None:
            nodes = circuit.dynamic_program
            cbit_num = circuit.cbit_num
        else:
            # Flat circuit: linear gates followed by terminal measurements
            # (c[i] receives the i-th measured qubit, matching flat OriginIR).
            nodes = [GateOp(op) for op in circuit.opcode_list]
            nodes = nodes + [MeasureOp(q, i) for i, q in enumerate(circuit.measure_list)]
            cbit_num = max(circuit.cbit_num, len(circuit.measure_list))

        return nodes, circuit.qubit_num, cbit_num, dict(circuit.qram_declarations)

    def _register_dynamic_qrams(self, qram_declarations: dict, qram_data: dict | None = None) -> None:
        from uniqc.circuit_builder.qram import QRAM

        self.qram_objects = {}
        self.opcode_simulator.qram_registry = {}
        for name, (addr_size, data_size) in qram_declarations.items():
            qram = QRAM(name, addr_size, data_size)
            self.qram_objects[name] = qram
            self.opcode_simulator.register_qram(name, addr_size, data_size, qram._data)
        if qram_data:
            for name, entries in qram_data.items():
                for addr, value in entries.items():
                    self.qram_objects[name].write(addr, value)

    def _apply_seed(self) -> None:
        if self.seed is not None:
            import uniqc_cpp

            uniqc_cpp.seed(self.seed)

    # ------------------------------------------------------------------
    # Tree interpreter
    # ------------------------------------------------------------------

    def _run_once(self, nodes, qubit_num, cbit_num, qram_declarations, qram_data=None) -> int:
        """Execute the program tree once from a fresh state; return CREG value."""
        self._register_dynamic_qrams(qram_declarations, qram_data)
        self.opcode_simulator.simulator.init_n_qubit(qubit_num)
        self.opcode_simulator.init_creg(cbit_num)
        self._run_body(nodes)
        return self.opcode_simulator.creg_value()

    def _run_body(self, nodes) -> None:
        for node in nodes:
            self._run_node(node)

    def _run_node(self, node) -> None:
        sim = self.opcode_simulator
        if isinstance(node, GateOp):
            operation, qubit, cbit, parameter, is_dagger, control_qubits_set = node.opcode
            sim.simulate_gate(operation, qubit, cbit, parameter, is_dagger, control_qubits_set)
        elif isinstance(node, MeasureOp):
            sim.simulate_measure(node.qubit, node.cbit)
        elif isinstance(node, ResetOp):
            sim.simulate_reset(node.qubit)
        elif isinstance(node, ClassicalOp):
            sim.simulate_classical(node)
        elif isinstance(node, IfBlock):
            if node.cond.evaluate(sim.creg):
                self._run_body(node.then_body)
            elif node.else_body is not None:
                self._run_body(node.else_body)
        elif isinstance(node, WhileBlock):
            cap = self.max_while_iterations if self.max_while_iterations is not None else node.max_iterations
            iterations = 0
            while node.cond.evaluate(sim.creg):
                iterations += 1
                if iterations > cap:
                    raise LoopWatchdogError(
                        f"QWHILE exceeded max_iterations={cap}. The loop condition "
                        f"{node.cond.to_str()} never became false."
                    )
                self._run_body(node.body)
        else:
            raise TypeError(f"Unknown program node: {node!r}")

    # ------------------------------------------------------------------
    # Public simulation API (per-shot sampling)
    # ------------------------------------------------------------------

    def simulate_single_shot(self, quantum_code) -> int:
        """Run the program once and return the final CREG bitstring as an int
        (``c[0]`` = LSB)."""
        nodes, qubit_num, cbit_num, qrams = self._resolve_program(quantum_code)
        self._apply_seed()
        return self._run_once(nodes, qubit_num, cbit_num, qrams)

    def simulate_shots(self, quantum_code, shots: int) -> dict[int, int]:
        """Run the program *shots* times and tally final CREG bitstrings.

        Returns:
            Dict mapping outcome bitstring (int, ``c[0]`` = LSB) to its count.
        """
        nodes, qubit_num, cbit_num, qrams = self._resolve_program(quantum_code)
        self._apply_seed()
        counts: dict[int, int] = {}
        for _ in range(shots):
            value = self._run_once(nodes, qubit_num, cbit_num, qrams)
            counts[value] = counts.get(value, 0) + 1
        return counts

    def simulate_statevector(self, quantum_code):
        """Run the program once and return the resulting statevector.

        Note: for programs with mid-circuit measurement this is a **single
        stochastic sample** (the post-collapse state of one run), not a
        deterministic object.
        """
        if self.opcode_simulator.simulator_typestr == "density_operator":
            raise ValueError("statevector is not available on the density backend; use simulate_density_matrix.")
        nodes, qubit_num, cbit_num, qrams = self._resolve_program(quantum_code)
        self._apply_seed()
        self._run_once(nodes, qubit_num, cbit_num, qrams)
        return np.array(self.opcode_simulator.simulator.state)

    def simulate_density_matrix(self, quantum_code):
        """Run the program once and return the resulting density matrix.

        For programs with mid-circuit measurement this is a single stochastic
        sample's density matrix.
        """
        nodes, qubit_num, cbit_num, qrams = self._resolve_program(quantum_code)
        self._apply_seed()
        self._run_once(nodes, qubit_num, cbit_num, qrams)
        state = np.array(self.opcode_simulator.simulator.state)
        if self.opcode_simulator.simulator_typestr == "density_operator":
            return np.reshape(state, (2**qubit_num, 2**qubit_num), order="C")
        return np.outer(state, np.conj(state))

    def _blocked(self, method: str):
        raise NotImplementedError(
            f"{method}() is not defined for a dynamic OriginIR-ext program "
            "(mid-circuit MEASURE + classical control flow make each run "
            "stochastic). Use simulate_shots() / simulate_single_shot() for "
            "per-shot sampling instead."
        )

    def simulate_pmeasure(self, quantum_code):
        """Blocked: exact measurement probabilities are ill-defined here."""
        self._blocked("simulate_pmeasure")

    def simulate_stateprob(self, quantum_code):
        """Blocked: exact state probabilities are ill-defined here."""
        self._blocked("simulate_stateprob")
