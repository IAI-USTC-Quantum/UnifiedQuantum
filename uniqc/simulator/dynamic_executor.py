"""Dynamic-program interpreter for OriginIR-ext.

Drives an :class:`~uniqc.simulator.opcode_simulator.OpcodeSimulator` through a
structured :mod:`uniqc.circuit_builder.dynamic_program` AST: gate/QRAM-call
opcodes, mid-circuit measurement (``CMeasureNode``) and reset (``ResetNode``),
classical assignment (``AssignNode``), and nested ``IfNode``/``WhileNode``
control flow, against a live statevector or density-matrix C++ backend.

Key exports:
    - ``DynamicProgramExecutor`` — stateful interpreter (reusable across
      several ``run()``/``run_with_restarts()`` calls against fresh states).
    - ``simulate_dynamic`` — convenience one-shot entry point.
    - ``LoopWatchdogError`` — raised when a ``QWHILE`` exceeds its
      configured ``max_iterations``.
    - ``ExecutionTrace`` / ``DynamicExecutionResult`` — execution bookkeeping.
"""

from __future__ import annotations

__all__ = [
    "LoopWatchdogError",
    "ExecutionTrace",
    "DynamicExecutionResult",
    "DynamicProgramExecutor",
    "simulate_dynamic",
]

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from uniqc.circuit_builder.dynamic_program import (
    AssignNode,
    CMeasureNode,
    GateNode,
    IfNode,
    ResetNode,
    WhileNode,
)
from uniqc.circuit_builder.qram import QRAM

from .opcode_simulator import OpcodeSimulator, backend_alias


class LoopWatchdogError(RuntimeError):
    """Raised when a QWHILE loop exceeds its configured max_iterations."""


@dataclass
class ExecutionTrace:
    """Chronological record of a dynamic-program execution."""

    steps: list[dict] = field(default_factory=list)
    if_true_count: int = 0
    if_false_count: int = 0
    while_iterations: int = 0
    while_exhausted_count: int = 0
    measurements: list[tuple[int, int]] = field(default_factory=list)
    resets: list[int] = field(default_factory=list)
    restarts: int = 0


@dataclass
class DynamicExecutionResult:
    """Outcome of running a dynamic program to completion (or exhaustion)."""

    memory: dict[str, int]
    trace: ExecutionTrace
    status: str  # "completed" | "restart_exhausted"
    statevector: object = None
    density_matrix: object = None


class DynamicProgramExecutor:
    """Interprets a :class:`~uniqc.circuit_builder.qcircuit.Circuit`'s
    structured dynamic program.

    Args:
        backend_type: ``"statevector"`` or ``"density_matrix"`` (see
            :func:`uniqc.simulator.opcode_simulator.backend_alias` for
            accepted aliases).

    Attributes:
        qram_objects: QRAM data containers registered by the most recent
            ``run()``/``run_with_restarts()`` call, keyed by name — write
            into these (``executor.qram_objects[name].write(addr, value)``)
            before running to pre-populate QRAM tables, or pass *qram_data*
            to ``run()``.
    """

    def __init__(self, backend_type: str = "statevector"):
        self.backend_type = backend_alias(backend_type)
        self.opcode_simulator = OpcodeSimulator(self.backend_type)
        self.qram_objects: dict[str, QRAM] = {}
        self.memory: dict[str, int] = {}
        self.trace: ExecutionTrace = ExecutionTrace()

    def _register_qram(self, qram_declarations: dict[str, tuple[int, int]]) -> None:
        self.qram_objects = {}
        self.opcode_simulator.qram_registry = {}
        for name, (addr_size, data_size) in qram_declarations.items():
            qram = QRAM(name, addr_size, data_size)
            self.qram_objects[name] = qram
            self.opcode_simulator.register_qram(name, addr_size, data_size, qram._data)

    def _finalize_result(self, circuit, status: str) -> DynamicExecutionResult:
        state = np.array(self.opcode_simulator.simulator.state)
        result = DynamicExecutionResult(memory=dict(self.memory), trace=self.trace, status=status)
        if self.backend_type == "statevector":
            result.statevector = state
        else:
            dim = 2**circuit.qubit_num
            result.density_matrix = state.reshape(dim, dim)
        return result

    def run(
        self,
        circuit,
        *,
        seed: int | None = None,
        memory: dict[str, int] | None = None,
        qram_data: dict[str, dict[int, int]] | None = None,
    ) -> DynamicExecutionResult:
        """Execute *circuit*'s dynamic program once from a fresh |0...0> state.

        Args:
            circuit: A ``Circuit`` with ``dynamic_program`` set. Ordinary
                flat circuits (``dynamic_program is None``) are also
                accepted and executed as a single top-level gate sequence.
            seed: Optional RNG seed for deterministic mid-circuit measurement
                and reset outcomes (forwarded to ``uniqc_cpp.seed``).
            memory: Optional initial classical memory, overriding
                ``circuit.classical_memory`` defaults.
            qram_data: Optional ``{qram_name: {addr: value}}`` used to
                pre-populate declared QRAM tables before execution.

        Returns:
            DynamicExecutionResult with final memory, execution trace, and
            final statevector/density matrix.

        Raises:
            ValueError: If *circuit* has any unclosed ``QIF``/``QWHILE``
                block (missing a matching ``endqif()``/``endqwhile()``).
        """
        if circuit.dynamic_program is not None:
            circuit.check_dynamic_program_closed()

        if seed is not None:
            import uniqc_cpp

            uniqc_cpp.seed(seed)

        self._register_qram(circuit.qram_declarations)
        if qram_data:
            for name, entries in qram_data.items():
                for addr, value in entries.items():
                    self.qram_objects[name].write(addr, value)

        self.opcode_simulator.simulator.init_n_qubit(circuit.qubit_num)
        self.memory = dict(memory) if memory is not None else dict(circuit.classical_memory)
        self.trace = ExecutionTrace()

        nodes = (
            circuit.dynamic_program
            if circuit.dynamic_program is not None
            else [GateNode(op) for op in circuit.opcode_list]
        )
        self._run_body(nodes)

        return self._finalize_result(circuit, status="completed")

    def run_with_restarts(
        self,
        circuit,
        *,
        max_restarts: int,
        success: Callable[[dict[str, int]], bool],
        seed: int | None = None,
        memory: dict[str, int] | None = None,
        qram_data: dict[str, dict[int, int]] | None = None,
    ) -> DynamicExecutionResult:
        """Repeatedly execute *circuit* from a fresh state until *success*.

        Models a bounded restart loop (e.g. rejection-sampling-style
        streaming filters, per the OriginIR-ext ``max_restarts`` contract):
        after each attempt, *success* is evaluated against the final
        classical memory. If it returns True the result is returned
        immediately with ``status="completed"``. Otherwise the whole
        program is re-run from a fresh |0...0> state (and reinitialized
        memory) up to *max_restarts* attempts; if every attempt fails, the
        returned result has ``status="restart_exhausted"``.

        Args:
            circuit: A ``Circuit`` with ``dynamic_program`` set.
            max_restarts: Maximum number of attempts (mandatory — mirrors
                OriginIR-ext's required ``max_restarts`` watchdog).
            success: Predicate over final classical memory deciding whether
                an attempt succeeded.
            seed: Optional RNG seed applied once before the first attempt;
                later attempts keep drawing from the same seeded stream, so
                the whole run remains fully deterministic.
            memory: Optional initial classical memory for every attempt.
            qram_data: Optional ``{qram_name: {addr: value}}`` to
                pre-populate declared QRAM tables before every attempt.

        Returns:
            DynamicExecutionResult with ``trace.restarts`` set to the number
            of attempts actually made.
        """
        if max_restarts < 1:
            raise ValueError("max_restarts must be >= 1.")
        if seed is not None:
            import uniqc_cpp

            uniqc_cpp.seed(seed)

        result: DynamicExecutionResult | None = None
        for attempt in range(1, max_restarts + 1):
            result = self.run(circuit, memory=memory, qram_data=qram_data)
            result.trace.restarts = attempt
            if success(result.memory):
                return result

        result.status = "restart_exhausted"
        return result

    # ------------------------------------------------------------------
    # Node interpreter
    # ------------------------------------------------------------------

    def _run_body(self, nodes: list) -> None:
        for node in nodes:
            self._run_node(node)

    def _run_node(self, node) -> None:
        if isinstance(node, GateNode):
            operation, qubit, cbit, parameter, is_dagger, control_qubits_set = node.opcode
            self.opcode_simulator.simulate_gate(operation, qubit, cbit, parameter, is_dagger, control_qubits_set)
            self.trace.steps.append({"type": "gate", "operation": operation})
        elif isinstance(node, CMeasureNode):
            outcome = self.opcode_simulator.simulator.measure_qubit(node.qubit)
            self.memory[node.mem] = outcome
            self.trace.measurements.append((node.qubit, outcome))
            self.trace.steps.append({"type": "cmeasure", "qubit": node.qubit, "mem": node.mem, "outcome": outcome})
        elif isinstance(node, ResetNode):
            self.opcode_simulator.simulator.reset_qubit(node.qubit)
            self.trace.resets.append(node.qubit)
            self.trace.steps.append({"type": "reset", "qubit": node.qubit})
        elif isinstance(node, AssignNode):
            value = node.expr.evaluate(self.memory)
            self.memory[node.mem] = value
            self.trace.steps.append({"type": "assign", "mem": node.mem, "value": value})
        elif isinstance(node, IfNode):
            cond = bool(node.cond.evaluate(self.memory))
            self.trace.steps.append({"type": "if", "cond": cond})
            if cond:
                self.trace.if_true_count += 1
                self._run_body(node.then_body)
            else:
                self.trace.if_false_count += 1
                if node.else_body is not None:
                    self._run_body(node.else_body)
        elif isinstance(node, WhileNode):
            iterations = 0
            while bool(node.cond.evaluate(self.memory)):
                iterations += 1
                if iterations > node.max_iterations:
                    self.trace.while_exhausted_count += 1
                    raise LoopWatchdogError(f"QWHILE exceeded max_iterations={node.max_iterations}.")
                self.trace.while_iterations += 1
                self._run_body(node.body)
            self.trace.steps.append({"type": "while_done", "iterations": iterations})
        else:
            raise TypeError(f"Unknown dynamic program node: {node!r}")


def simulate_dynamic(
    circuit,
    backend_type: str = "statevector",
    seed: int | None = None,
    memory: dict[str, int] | None = None,
    qram_data: dict[str, dict[int, int]] | None = None,
) -> DynamicExecutionResult:
    """Convenience one-shot entry point: run *circuit*'s dynamic program once.

    Args:
        circuit: A ``Circuit`` (with or without a structured dynamic
            program — ordinary flat circuits are executed as a single
            top-level gate sequence).
        backend_type: ``"statevector"`` or ``"density_matrix"``.
        seed: Optional RNG seed for deterministic execution.
        memory: Optional initial classical memory, overriding
            ``circuit.classical_memory`` defaults.
        qram_data: Optional ``{qram_name: {addr: value}}`` to pre-populate
            declared QRAM tables before execution.

    Returns:
        DynamicExecutionResult.
    """
    executor = DynamicProgramExecutor(backend_type)
    return executor.run(circuit, seed=seed, memory=memory, qram_data=qram_data)
