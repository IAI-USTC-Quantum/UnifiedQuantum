"""Quantum circuit builder with OriginIR and OpenQASM 2.0 output.

This module provides a Circuit class for building quantum circuits programmatically.
It supports various quantum gates, controlled operations, dagger (adjoint) blocks,
and measurement operations. The circuit can be exported to OriginIR or OpenQASM format.

Key exports:
    Circuit: Main quantum circuit builder class.
    OpcodeType: Type alias for opcode tuples.
"""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Union

from .opcode import (
    make_header_originir,
    make_header_qasm,
    make_measure_originir,
    make_measure_qasm,
    opcode_to_line_originir,
    opcode_to_line_originir_official,
    opcode_to_line_qasm,
)

if TYPE_CHECKING:
    from .parameter import Parameters
    from .qubit import QReg, QRegSlice, Qubit

    try:
        import qiskit

        _QiskitCircuit = qiskit.QuantumCircuit
    except ImportError:
        _QiskitCircuit = None  # type: ignore[assignment,misc]
    try:
        from pyqpanda3.intermediate_compiler import (
            QProg as _PyQProg,
        )

        _PyQCircuit = _PyQProg
    except ImportError:
        _PyQCircuit = None  # type: ignore[assignment,misc]
else:
    _QiskitCircuit = None
    _PyQCircuit = None

# Opcode: (op_name, qubits, cbits, params, dagger, control_qubits)
QubitSpec = int | list[int]
CbitSpec = int | list[int] | None
ParamSpec = float | list[float] | tuple[float, ...] | None
OpCode = tuple[str, QubitSpec, CbitSpec, ParamSpec, bool, QubitSpec]

# Extended types for Qubit/QRegSlice support
QubitInput = Union[int, "Qubit", "QRegSlice", list]

# The universal circuit input type accepted by :func:`~uniqc.compile.compile`,
# :class:`~uniqc.simulator.Simulator`, and :func:`~uniqc.submit_task`.
#
# At runtime this is ``Union[Circuit, str]``.  ``qiskit.QuantumCircuit`` and
# ``pyqpanda3.QProg`` are also accepted but are resolved at type-check time
# only (via ``TYPE_CHECKING``) to avoid hard import requirements.
#
# See :class:`Circuit` class docstring for full details.
AnyQuantumCircuit = Union["Circuit", str]

__all__ = ["Circuit", "OpcodeType", "AnyQuantumCircuit"]

# Backward-compatible type alias
OpcodeType = OpCode


class CircuitControlContext:
    """Context manager for controlled gate blocks."""

    c: Circuit
    control_list: tuple[int, ...]

    def __init__(self, c: Circuit, control_list: tuple[int, ...]) -> None:
        self.c = c
        self.control_list = control_list

    def _qubit_list(self) -> str:
        ret = ""
        for q in self.control_list:
            ret += f"q[{q}], "
        return ret[:-2]

    def __enter__(self) -> None:
        # Keep circuit_str for backward-compat with tests that inspect it directly.
        ret = "CONTROL " + self._qubit_list() + "\n"
        self.c.circuit_str += ret
        # Push controls onto active-control stack so add_gate can merge them.
        self.c._control_stack.append(tuple(self.control_list))
        self.c._active_controls = self.c._active_controls + list(self.control_list)

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore[no-untyped-def]
        self.c.circuit_str += "ENDCONTROL\n"
        # Pop the controls this context pushed.
        if self.c._control_stack:
            popped = self.c._control_stack.pop()
            self.c._active_controls = self.c._active_controls[: len(self.c._active_controls) - len(popped)]


class CircuitDagContext:
    """Context manager for dagger (adjoint) gate blocks."""

    c: Circuit

    def __init__(self, c: Circuit) -> None:
        self.c = c

    def __enter__(self) -> None:
        self.c.circuit_str += "DAGGER\n"
        self.c._active_dagger = not self.c._active_dagger

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore[no-untyped-def]
        self.c.circuit_str += "ENDDAGGER\n"
        self.c._active_dagger = not self.c._active_dagger


class Circuit:
    """Quantum circuit builder that generates OriginIR and OpenQASM output.

    Attributes
    ----------
    used_qubit_list : list[int]
        Qubits referenced in the circuit.
    circuit_str : str
        Raw string builder used by context managers.
    max_qubit : int
        Highest qubit index used.
    qubit_num : int
        Total number of qubits.
    cbit_num : int
        Total number of classical bits.
    measure_list : list[int]
        Qubits scheduled for measurement.
    opcode_list : list[OpCode]
        Internal list of gate opcodes.
    _qregs : dict[str, QReg]
        Named quantum registers (if created with qregs parameter).

    .. rubric:: AnyQuantumCircuit — the universal input type

    Most public APIs (:func:`~uniqc.compile.compile`,
    :class:`~uniqc.simulator.Simulator`, :func:`~uniqc.submit_task`)
    accept :data:`AnyQuantumCircuit`, which is a union of:

    * :class:`Circuit` — this class
    * ``str`` — OriginIR or OpenQASM 2.0 (auto-detected from content)
    * ``qiskit.QuantumCircuit`` — converted via QASM round-trip
    * ``pyqpanda3.QProg`` — converted via OriginIR round-trip

    Use :meth:`to_qiskit_circuit` or :meth:`to_pyqpanda3_circuit` to
    convert back to external formats.
    """

    used_qubit_list: list[int]
    circuit_str: str
    max_qubit: int
    qubit_num: int
    cbit_num: int
    measure_list: list[int]
    opcode_list: list[OpCode]
    _qregs: dict[str, QReg]

    def __init__(
        self,
        qregs: dict[str, int] | list[QReg] | int | None = None,
        param_dict: dict[str, object] | None = None,
    ) -> None:
        """Initialize a quantum circuit.

        Args:
            qregs: Optional qubit register specification. Can be:
                - dict[str, int]: Mapping of register names to sizes, e.g., {"a": 4, "b": 2}
                - list[QReg]: List of QReg objects
                - int: Total number of qubits (backward compatible)
                - None: No predefined registers (backward compatible)
            param_dict: Optional mapping of parameter names to ``torch.Tensor``
                values.  Gate methods accept parameter names (strings) which
                are resolved through this dict and auto-registered in
                :pyattr:`param_map`.

        Examples:
            >>> # Backward compatible - no registers
            >>> c = Circuit()

            >>> # Backward compatible - fixed qubit count
            >>> c = Circuit(4)

            >>> # Named registers
            >>> c = Circuit(qregs={"data": 4, "ancilla": 2})

            >>> # Using QReg objects
            >>> from uniqc.circuit_builder import QReg
            >>> qr_a = QReg(name="a", size=4)
            >>> c = Circuit(qregs=[qr_a])

            >>> # Differentiable circuit with named parameters
            >>> params = {"theta": nn.Parameter(torch.tensor(0.5))}
            >>> c = Circuit(1, param_dict=params)
            >>> c.ry(0, "theta")
        """
        from .qubit import QReg as QRegClass

        self.used_qubit_list = []
        self.max_qubit = 0
        self.qubit_num = 0
        self.cbit_num = 0
        self.measure_list = []
        self.opcode_list = []
        self.circuit_str = ""
        # Named register storage
        self._qregs = {}
        # Active-context state: accumulated control qubits and dagger flag for
        # gates added inside with-control / with-dagger blocks.
        self._active_controls: list[int] = []
        self._active_dagger: bool = False
        # Stack used by set_control / unset_control to remember each push size.
        self._control_stack: list[tuple[int, ...]] = []
        # Named parameters attached to this circuit (for parametric circuits)
        self._params: Parameters | None = None
        # Tensor parameter map: opcode index -> torch.Tensor
        # Enables differentiable circuit execution (no hard torch dependency).
        self.param_map: dict = {}
        # Named parameter dict (optional) for name-based gate param references.
        self._param_dict: dict[str, object] | None = param_dict
        # Auto-created nn.Parameters keyed by ("GATE_NAME", opcode_idx).
        self._auto_params: dict[tuple[str, int], object] = {}
        # QRAM declarations: name -> (addr_size, data_size)
        self.qram_declarations: dict[str, tuple[int, int]] = {}

        # Handle qregs parameter
        if qregs is not None:
            if isinstance(qregs, int):
                # Backward compatible: Circuit(4) sets qubit_num directly
                self.qubit_num = qregs
                self.max_qubit = max(0, qregs - 1)
            elif isinstance(qregs, dict):
                # Create QReg objects from dict
                base_index = 0
                for name, size in qregs.items():
                    qreg = QRegClass(name=name, size=size, base_index=base_index)
                    self._qregs[name] = qreg
                    base_index += size
                self.qubit_num = base_index
                self.max_qubit = max(0, base_index - 1)
            elif isinstance(qregs, list):
                # Use provided QReg objects, updating base_index
                base_index = 0
                for qreg in qregs:
                    qreg.base_index = base_index
                    self._qregs[qreg.name] = qreg
                    base_index += qreg.size
                self.qubit_num = base_index
                self.max_qubit = max(0, base_index - 1)

    @property
    def qregs(self) -> dict[str, QReg]:
        """Return the named quantum registers."""
        return self._qregs

    def get_qreg(self, name: str) -> QReg:
        """Get a named quantum register by name.

        Args:
            name: Register name

        Returns:
            QReg object

        Raises:
            KeyError: If register name not found
        """
        if name not in self._qregs:
            raise KeyError(f"QReg '{name}' not found. Available: {list(self._qregs.keys())}")
        return self._qregs[name]

    def _resolve_qubit(self, qubit: QubitInput) -> int | list[int]:
        """Resolve a qubit reference to integer index(es).

        Args:
            qubit: Qubit reference - can be int, Qubit, QReg, QRegSlice, or list

        Returns:
            Integer qubit index or list of indices
        """
        from .qubit import QReg as QRegClass
        from .qubit import QRegSlice as QRegSliceClass
        from .qubit import Qubit as QubitClass

        if isinstance(qubit, int):
            return qubit
        elif isinstance(qubit, QubitClass):
            return int(qubit)
        elif isinstance(qubit, QRegClass):
            # QReg - return all qubit indices
            return [int(q) for q in qubit.qubits]
        elif isinstance(qubit, QRegSliceClass):
            return [int(q) for q in qubit]
        elif isinstance(qubit, list):
            # Recursively resolve list elements
            resolved = []
            for q in qubit:
                if isinstance(q, int):
                    resolved.append(q)
                elif isinstance(q, QubitClass):
                    resolved.append(int(q))
                elif isinstance(q, QRegClass):
                    resolved.extend(int(qi) for qi in q.qubits)
                elif isinstance(q, QRegSliceClass):
                    resolved.extend(int(qi) for qi in q)
                else:
                    raise TypeError(f"Unsupported qubit type in list: {type(q)}")
            return resolved
        else:
            raise TypeError(f"Unsupported qubit type: {type(qubit)}")

    def copy(self) -> Circuit:
        """Return a deep copy of this circuit."""
        new_circuit = Circuit()
        new_circuit.used_qubit_list = self.used_qubit_list.copy()
        new_circuit.max_qubit = self.max_qubit
        new_circuit.qubit_num = self.qubit_num
        new_circuit.cbit_num = self.cbit_num
        new_circuit.measure_list = self.measure_list.copy()
        new_circuit.opcode_list = self.opcode_list.copy()
        new_circuit.circuit_str = self.circuit_str
        new_circuit._active_controls = self._active_controls.copy()
        new_circuit._active_dagger = self._active_dagger
        new_circuit._control_stack = list(self._control_stack)
        new_circuit.param_map = dict(self.param_map)
        new_circuit._param_dict = self._param_dict  # shared reference
        new_circuit._auto_params = dict(self._auto_params)
        return new_circuit

    def _make_originir_circuit(self) -> str:
        qram_header = ""
        for name, (addr_size, data_size) in self.qram_declarations.items():
            qram_header += f"QRAMDECL {name} {addr_size},{data_size}\n"
        header = qram_header + make_header_originir(self.qubit_num, self.cbit_num)
        circuit_str = "\n".join([opcode_to_line_originir(op) for op in self.opcode_list])
        measure = make_measure_originir(self.measure_list)
        return header + circuit_str + "\n" + measure

    def _make_qasm_circuit(self) -> str:
        from .translate_qasm2_oir import collect_qasm2_custom_gates

        custom_gates = collect_qasm2_custom_gates(self.opcode_list)
        header = make_header_qasm(self.qubit_num, self.cbit_num, custom_gates=custom_gates)
        circuit_str = "\n".join([opcode_to_line_qasm(op, self.qubit_num) for op in self.opcode_list])
        measure = make_measure_qasm(self.measure_list)
        return header + circuit_str + "\n" + measure

    def _make_originir_official_circuit(self) -> str:
        """Generate strict official OriginIR — decompose ext gates, block format."""
        from uniqc.compile.decompose import decompose_for_originir

        decomposed = decompose_for_originir(self)
        header = make_header_originir(decomposed.qubit_num, decomposed.cbit_num)
        circuit_str = "\n".join(
            [opcode_to_line_originir_official(op) for op in decomposed.opcode_list]
        )
        measure = make_measure_originir(decomposed.measure_list)
        return header + circuit_str + "\n" + measure

    @property
    def circuit(self) -> str:
        """Generate the circuit in OriginIR format."""
        return self._make_originir_circuit()

    @property
    def originir(self) -> str:
        """Generate the circuit in OriginIR format."""
        return self._make_originir_circuit()

    @property
    def qasm(self) -> str:
        """Generate the circuit in OpenQASM format."""
        return self._make_qasm_circuit()

    @classmethod
    def from_qasm(cls, qasm_str: str) -> Circuit:
        """Create a Circuit from an OpenQASM 2.0 string.

        Args:
            qasm_str: OpenQASM 2.0 formatted circuit string.

        Returns:
            A new Circuit instance.
        """
        from uniqc.compile.qasm.qasm_base_parser import OpenQASM2_BaseParser

        parser = OpenQASM2_BaseParser()
        parser.parse(qasm_str)
        return parser.to_circuit()

    @classmethod
    def from_originir(cls, originir_str: str) -> Circuit:
        """Create a Circuit from an OriginIR string.

        Args:
            originir_str: OriginIR formatted circuit string.

        Returns:
            A new Circuit instance.
        """
        from uniqc.compile.originir.originir_base_parser import OriginIR_BaseParser

        parser = OriginIR_BaseParser()
        parser.parse(originir_str)
        return parser.to_circuit()

    def to_qasm(self) -> str:
        """Export the circuit as an OpenQASM 2.0 string."""
        return self.qasm

    def to_originir(self) -> str:
        """Export the circuit as an OriginIR string."""
        return self.originir

    def to_extended_originir(self) -> str:
        """Export the circuit in extended OriginIR format (full form with QINIT/CREG/MEASURE)."""
        return self.originir

    def to_originir_official(self) -> str:
        """Export the circuit as strict official OriginIR.

        Extended gates are decomposed to the official gate set, and inline
        ``dagger`` / ``controlled_by`` syntax is replaced with block-level
        ``DAGGER`` / ``CONTROL`` delimiters.  The output is suitable for
        submission to OriginQ cloud.
        """
        return self._make_originir_official_circuit()

    @property
    def originir_official(self) -> str:
        """Generate the circuit in strict official OriginIR format."""
        return self._make_originir_official_circuit()

    @classmethod
    def from_originir_ext(cls, originir_ext_str: str) -> Circuit:
        """Create a Circuit from an OriginIR-ext string.

        Equivalent to :meth:`from_originir` — both parse the same
        superset syntax.  This alias makes the intent explicit when
        working with OriginIR-ext source.
        """
        return cls.from_originir(originir_ext_str)

    def to_qiskit_circuit(self):
        """Convert to a ``qiskit.QuantumCircuit``.

        Returns:
            qiskit.QuantumCircuit equivalent of this circuit.

        Raises:
            ImportError: If qiskit is not installed.
        """
        try:
            from qiskit import qasm2
        except ImportError:
            raise ImportError(
                "qiskit is required for to_qiskit_circuit(). Install it with: pip install qiskit"
            ) from None
        return qasm2.loads(self.qasm)

    def to_pyqpanda3_circuit(self):
        """Convert to a pyqpanda3 ``QProg``.

        Returns:
            pyqpanda3 QProg equivalent of this circuit.

        Raises:
            ImportError: If pyqpanda3 is not installed.
        """
        try:
            from pyqpanda3.intermediate_compiler import (
                convert_originir_string_to_qprog,
            )
        except ImportError:
            raise ImportError(
                "pyqpanda3 is required for to_pyqpanda3_circuit(). Install it with: pip install pyqpanda3"
            ) from None
        return convert_originir_string_to_qprog(self.originir)

    def record_qubit(self, qubits: int | list[int]) -> None:
        """Record the qubits used in the circuit."""
        for qubit in qubits if isinstance(qubits, list) else [qubits]:
            if qubit not in self.used_qubit_list:
                self.used_qubit_list.append(qubit)
                self.max_qubit = max(self.max_qubit, qubit)
        self.qubit_num = self.max_qubit + 1

    def _resolve_param_strings(self, params: ParamSpec) -> ParamSpec:
        """Resolve string parameter names via ``_param_dict``.

        Returns the params with any name strings replaced by the corresponding
        tensor/value from ``_param_dict``.  If no ``_param_dict`` is set or
        params contains no strings, returns *params* unchanged.
        """
        if params is None or self._param_dict is None:
            return params
        if isinstance(params, str):
            return self._param_dict[params]
        if isinstance(params, (list, tuple)):
            resolved = [self._param_dict[p] if isinstance(p, str) else p for p in params]
            return type(params)(resolved)  # preserve list/tuple type
        return params

    def add_gate(
        self,
        operation: str,
        qubits: QubitInput,
        cbits: CbitSpec = None,
        params: ParamSpec = None,
        dagger: bool = False,
        control_qubits: QubitInput = None,
        has_param: bool = False,
        trainable: bool = True,
        init_params: object = None,
    ) -> None:
        """Add a gate to the circuit.

        Args:
            operation: Gate name (e.g., "H", "CNOT", "RX")
            qubits: Target qubit(s) - can be int, Qubit, QRegSlice, or list
            cbits: Classical bit(s) for measurement
            params: Gate parameters
            dagger: Whether to apply dagger (adjoint)
            control_qubits: Control qubit(s)
            has_param: If *True*, automatically create an ``nn.Parameter`` for
                this gate's rotation angle(s).  The created parameter is stored
                in :pyattr:`_auto_params` and registered in :pyattr:`param_map`.
                Requires PyTorch.
            trainable: Whether the auto-created parameter is trainable
                (``requires_grad``).  Only used when *has_param=True*.
            init_params: Custom initial value(s) for the auto-created parameter.
                A scalar or list/tuple matching the gate's *num_params*.
                Defaults to ``Uniform(-π, π)`` (TorchQuantum convention).
                Only used when *has_param=True*.
        """
        # Resolve qubit references to integers
        resolved_qubits = self._resolve_qubit(qubits)
        resolved_controls = self._resolve_qubit(control_qubits) if control_qubits is not None else None

        if operation in {"BARRIER", "I"} or operation in self.qram_declarations:
            # These gates have no controlled / dagger semantics; store as-is.
            merged_controls: QubitSpec = resolved_controls
            merged_dagger = dagger
        else:
            # Merge explicit control_qubits with any active context controls.
            base: list[int] = list(resolved_controls) if resolved_controls is not None else []
            if self._active_controls:
                overlap = set(base) & set(self._active_controls)
                if overlap:
                    raise ValueError(
                        f"Qubit(s) {sorted(overlap)} appear in both "
                        "control_qubits and an enclosing control() context block."
                    )
                base = base + list(self._active_controls)
            merged_controls = base if base else None  # type: ignore[assignment]
            # XOR active-dagger with the explicit dagger flag.
            merged_dagger = dagger ^ self._active_dagger
        # Resolve string param names via _param_dict, then detect tensors.
        opcode_params = self._resolve_param_strings(params)
        _has_torch = "torch" in __import__("sys").modules
        if _has_torch and opcode_params is not None:
            import torch as _torch
            if isinstance(opcode_params, _torch.Tensor):
                opcode_idx = len(self.opcode_list)
                self.param_map[opcode_idx] = opcode_params
                opcode_params = float(opcode_params.detach().cpu().item())
            elif isinstance(opcode_params, (list, tuple)) and any(isinstance(p, _torch.Tensor) for p in opcode_params):
                opcode_idx = len(self.opcode_list)
                self.param_map[opcode_idx] = _torch.stack(
                    [p if isinstance(p, _torch.Tensor) else _torch.tensor(float(p)) for p in opcode_params]
                )
                opcode_params = [float(p.detach().cpu().item()) if isinstance(p, _torch.Tensor) else float(p) for p in opcode_params]

        # has_param: auto-create nn.Parameter and register in param_map.
        if has_param:
            opcode_idx = len(self.opcode_list)
            if opcode_params is None:
                opcode_params = self._auto_init_param(
                    operation, opcode_idx,
                    trainable=trainable, init_params=init_params,
                )
            elif not _has_torch:
                raise ImportError("has_param requires PyTorch. Install with: pip install unified-quantum[pytorch]")

        opcode: OpCode = (operation, resolved_qubits, cbits, opcode_params, merged_dagger, merged_controls)  # type: ignore[assignment]
        self.opcode_list.append(opcode)
        self.record_qubit(resolved_qubits if isinstance(resolved_qubits, list) else [resolved_qubits])

    def add_circuit(self, other: Circuit) -> None:
        """Add all gates from another circuit into this circuit."""
        for op in other.opcode_list:
            self.add_gate(*op)

    # ------------------------------------------------------------------
    # Tensor parameter support (for differentiable circuit execution)
    # ------------------------------------------------------------------

    def set_param(self, opcode_idx: int, tensor) -> None:
        """Register a differentiable tensor for the parametric gate at *opcode_idx*.

        Args:
            opcode_idx: Index into :pyattr:`opcode_list`.
            tensor: A ``torch.Tensor`` (typically with ``requires_grad=True``).

        Raises:
            IndexError: If *opcode_idx* is out of range.
        """
        if opcode_idx < 0 or opcode_idx >= len(self.opcode_list):
            raise IndexError(
                f"opcode_idx {opcode_idx} out of range [0, {len(self.opcode_list)})"
            )
        self.param_map[opcode_idx] = tensor

    def set_param_last(self, tensor) -> int:
        """Register a tensor for the most recently added gate.

        Convenience wrapper around :pymeth:`set_param` for the common pattern
        of registering a parameter immediately after adding a gate.

        Returns:
            The opcode index that was registered.

        Raises:
            IndexError: If the circuit has no gates.
        """
        if not self.opcode_list:
            raise IndexError("Cannot set_param_last on an empty circuit (no gates)")
        idx = len(self.opcode_list) - 1
        self.param_map[idx] = tensor
        return idx

    def get_param(self, opcode_idx: int):
        """Get the tensor parameter registered for *opcode_idx*.

        Raises:
            KeyError: If no tensor is registered for this opcode.
        """
        return self.param_map[opcode_idx]

    @property
    def tensor_params(self) -> list:
        """Return all registered tensor parameters (for passing to an optimizer)."""
        return list(self.param_map.values())

    def has_tensor_params(self) -> bool:
        """Check whether this circuit has any registered tensor parameters."""
        return len(self.param_map) > 0

    # ---- has_param auto-initialization ---------------------------------------

    # Number of rotation angles per parametric gate.
    _PARAM_COUNTS: dict[str, int] = {
        "RX": 1, "RY": 1, "RZ": 1, "U1": 1,
        "RPhi": 2, "U2": 2,
        "U3": 3,
        "XX": 1, "YY": 1, "ZZ": 1,
    }

    def _auto_init_param(
        self,
        gate_name: str,
        opcode_idx: int,
        trainable: bool = True,
        init_params: object = None,
    ):
        """Create an ``nn.Parameter`` for *gate_name* and register it.

        Shape follows TorchQuantum convention: ``[1, num_params]``.
        Default initialization: ``Uniform(-π, π)`` when *init_params* is *None*.

        Returns a float placeholder for the opcode ``params`` field.
        """
        import math as _math
        import torch as _torch
        n = self._PARAM_COUNTS.get(gate_name, 1)
        if init_params is not None:
            if isinstance(init_params, (list, tuple)):
                p = _torch.nn.Parameter(_torch.tensor(init_params, dtype=_torch.float32).reshape(1, -1))
            else:
                p = _torch.nn.Parameter(_torch.full((1, n), float(init_params), dtype=_torch.float32))
        else:
            p = _torch.nn.Parameter(_torch.empty(1, n).uniform_(-_math.pi, _math.pi))
        p.requires_grad = trainable
        self._auto_params[(gate_name, opcode_idx)] = p
        # param_map stores the squeezed view for the simulator
        self.param_map[opcode_idx] = p.squeeze(0) if n > 1 else p[0, 0]
        vals = p.detach().cpu().flatten().tolist()
        return vals[0] if n == 1 else vals

    @property
    def params(self) -> list:
        """All auto-created ``nn.Parameter`` tensors (flat list for optimizers)."""
        return list(self._auto_params.values())

    def get_params_by_gate(self, gate_name: str) -> list:
        """Return auto-created parameters for gates named *gate_name*.

        Example::

            >>> c = Circuit(2)
            >>> c.ry(0, has_param=True)
            >>> c.ry(1, has_param=True)
            >>> c.rz(0, has_param=True)
            >>> len(c.get_params_by_gate("RY"))
            2
        """
        gate_upper = gate_name.upper()
        return [p for (g, _), p in self._auto_params.items() if g == gate_upper]

    @property
    def param_dict(self) -> dict[str, object] | None:
        """The named parameter dictionary, if provided at construction."""
        return self._param_dict

    @param_dict.setter
    def param_dict(self, value: dict[str, object] | None) -> None:
        self._param_dict = value

    @property
    def depth(self) -> int:
        """Calculate the depth of the quantum circuit."""
        qubit_depths: dict[int, int] = {}

        for opcode in self.opcode_list:
            op_name, qubits, _, _, _, control_qubits = opcode

            if op_name in ("I", "BARRIER") or op_name in self.qram_declarations:
                continue

            if not isinstance(qubits, list):
                qubits = [qubits]

            all_qubits = qubits + list(control_qubits) if control_qubits else qubits

            current_max_depth = 0
            for q in all_qubits:
                current_max_depth = max(current_max_depth, qubit_depths.get(q, 0))

            for q in all_qubits:
                qubit_depths[q] = current_max_depth + 1

        if not qubit_depths:
            return 0
        return max(qubit_depths.values())

    def get_matrix(self):
        """Return the full unitary matrix of this circuit as ``np.ndarray``.

        Qubit 0 is treated as the least-significant bit of the statevector index.
        The returned matrix uses the convention ``state_out = U @ state_in`` and
        gates are applied in the same order as ``opcode_list``.

        Raises:
            NotMatrixableError: If the circuit contains MEASURE / CONTROL /
                DAGGER scope opcodes that have no unitary representation.
        """
        from .matrix import get_matrix as _get_matrix

        return _get_matrix(self)

    # ─────────────────── Single-qubit gates (no parameters) ───────────────────

    def identity(self, qn: QubitInput) -> None:
        """Apply the identity (no-op) gate to qubit.

        Args:
            qn: Target qubit - can be int, Qubit, or QRegSlice
        """
        self.add_gate("I", qn)

    def h(self, qn: QubitInput) -> None:
        """Apply single-qubit Hadamard gate to qubit.

        Args:
            qn: Target qubit - can be int, Qubit, or QRegSlice
        """
        self.add_gate("H", qn)

    def x(self, qn: QubitInput) -> None:
        """Apply Pauli-X (NOT) gate to qubit.

        Args:
            qn: Target qubit - can be int, Qubit, or QRegSlice
        """
        self.add_gate("X", qn)

    def y(self, qn: QubitInput) -> None:
        """Apply Pauli-Y gate to qubit.

        Args:
            qn: Target qubit - can be int, Qubit, or QRegSlice
        """
        self.add_gate("Y", qn)

    def z(self, qn: QubitInput) -> None:
        """Apply Pauli-Z gate to qubit.

        Args:
            qn: Target qubit - can be int, Qubit, or QRegSlice
        """
        self.add_gate("Z", qn)

    def sx(self, qn: QubitInput) -> None:
        """Apply square-root-of-X (SX) gate to qubit.

        Args:
            qn: Target qubit - can be int, Qubit, or QRegSlice
        """
        self.add_gate("SX", qn)

    def sxdg(self, qn: QubitInput) -> None:
        """Apply conjugate-transpose of SX gate to qubit.

        Args:
            qn: Target qubit - can be int, Qubit, or QRegSlice
        """
        self.add_gate("SX", qn, dagger=True)

    def s(self, qn: QubitInput) -> None:
        """Apply S (phase) gate to qubit.

        Args:
            qn: Target qubit - can be int, Qubit, or QRegSlice
        """
        self.add_gate("S", qn)

    def sdg(self, qn: QubitInput) -> None:
        """Apply S-dagger (inverse phase) gate to qubit.

        Args:
            qn: Target qubit - can be int, Qubit, or QRegSlice
        """
        self.add_gate("S", qn, dagger=True)

    def t(self, qn: QubitInput) -> None:
        """Apply T gate to qubit.

        Args:
            qn: Target qubit - can be int, Qubit, or QRegSlice
        """
        self.add_gate("T", qn)

    def tdg(self, qn: QubitInput) -> None:
        """Apply T-dagger (inverse T) gate to qubit.

        Args:
            qn: Target qubit - can be int, Qubit, or QRegSlice
        """
        self.add_gate("T", qn, dagger=True)

    # ─────────────────── Single-qubit parametric gates ───────────────────

    def rx(self, qn: QubitInput, theta: float = None, *, has_param: bool = False,
           trainable: bool = True, init_params: object = None) -> None:
        """Apply RX rotation gate.

        Args:
            qn: Target qubit - can be int, Qubit, or QRegSlice
            theta: Rotation angle in radians.  Omit when *has_param=True*.
            has_param: Auto-create an ``nn.Parameter`` for this gate.
            trainable: Whether the parameter is trainable (only with *has_param*).
            init_params: Custom initial value.  Default: ``Uniform(-π, π)``.
        """
        self.add_gate("RX", qn, params=theta, has_param=has_param,
                       trainable=trainable, init_params=init_params)

    def ry(self, qn: QubitInput, theta: float = None, *, has_param: bool = False,
           trainable: bool = True, init_params: object = None) -> None:
        """Apply RY rotation gate."""
        self.add_gate("RY", qn, params=theta, has_param=has_param,
                       trainable=trainable, init_params=init_params)

    def rz(self, qn: QubitInput, theta: float = None, *, has_param: bool = False,
           trainable: bool = True, init_params: object = None) -> None:
        """Apply RZ rotation gate."""
        self.add_gate("RZ", qn, params=theta, has_param=has_param,
                       trainable=trainable, init_params=init_params)

    def rphi(self, qn: QubitInput, theta: float = None, phi: float = None, *,
             has_param: bool = False, trainable: bool = True, init_params: object = None) -> None:
        """Apply RPhi rotation gate."""
        params = [theta, phi] if not has_param else None
        self.add_gate("RPhi", qn, params=params, has_param=has_param,
                       trainable=trainable, init_params=init_params)

    def p(self, qn: QubitInput, lam: float) -> None:
        """Apply phase gate P(λ), equivalent to U1.

        Args:
            qn: Target qubit - can be int, Qubit, or QRegSlice
            lam: Phase angle in radians.
        """
        self.add_gate("U1", qn, params=lam)

    # ─────────────────── Two-qubit gates ───────────────────

    def cnot(self, controller: QubitInput, target: QubitInput) -> None:
        """Apply CNOT (controlled-X) gate.

        Args:
            controller: Control qubit - can be int, Qubit, or QRegSlice
            target: Target qubit - can be int, Qubit, or QRegSlice
        """
        self.add_gate("CNOT", [controller, target])

    def cx(self, controller: QubitInput, target: QubitInput) -> None:
        """Apply CX gate (alias for CNOT).

        Args:
            controller: Control qubit - can be int, Qubit, or QRegSlice
            target: Target qubit - can be int, Qubit, or QRegSlice
        """
        self.cnot(controller, target)

    def cz(self, q1: QubitInput, q2: QubitInput) -> None:
        """Apply controlled-Z gate to two qubits.

        Args:
            q1: First qubit - can be int, Qubit, or QRegSlice
            q2: Second qubit - can be int, Qubit, or QRegSlice
        """
        self.add_gate("CZ", [q1, q2])

    def iswap(self, q1: QubitInput, q2: QubitInput) -> None:
        """Apply iSWAP gate to two qubits.

        Args:
            q1: First qubit - can be int, Qubit, or QRegSlice
            q2: Second qubit - can be int, Qubit, or QRegSlice
        """
        self.add_gate("ISWAP", [q1, q2])

    def swap(self, q1: QubitInput, q2: QubitInput) -> None:
        """Apply SWAP gate to two qubits.

        Args:
            q1: First qubit - can be int, Qubit, or QRegSlice
            q2: Second qubit - can be int, Qubit, or QRegSlice
        """
        self.add_gate("SWAP", [q1, q2])

    # ─────────────────── Controlled parametric gates ───────────────────

    def crx(self, control: QubitInput, target: QubitInput, theta: float) -> None:
        """Apply controlled-RX gate.

        Args:
            control: Control qubit.
            target: Target qubit.
            theta: Rotation angle in radians.
        """
        self.add_gate("RX", target, params=theta, control_qubits=[control])

    def cry(self, control: QubitInput, target: QubitInput, theta: float) -> None:
        """Apply controlled-RY gate.

        Args:
            control: Control qubit.
            target: Target qubit.
            theta: Rotation angle in radians.
        """
        self.add_gate("RY", target, params=theta, control_qubits=[control])

    def crz(self, control: QubitInput, target: QubitInput, theta: float) -> None:
        """Apply controlled-RZ gate.

        Args:
            control: Control qubit.
            target: Target qubit.
            theta: Rotation angle in radians.
        """
        self.add_gate("RZ", target, params=theta, control_qubits=[control])

    def cp(self, control: QubitInput, target: QubitInput, lam: float) -> None:
        """Apply controlled-phase gate (equivalent to CU1).

        Args:
            control: Control qubit.
            target: Target qubit.
            lam: Phase angle in radians.
        """
        self.add_gate("U1", target, params=lam, control_qubits=[control])

    def cu(self, control: QubitInput, target: QubitInput, theta: float, phi: float, lam: float) -> None:
        """Apply controlled-U3 gate.

        Args:
            control: Control qubit.
            target: Target qubit.
            theta: Rotation angle in radians.
            phi: Phi angle in radians.
            lam: Lambda angle in radians.
        """
        self.add_gate("U3", target, params=[theta, phi, lam], control_qubits=[control])

    # ─────────────────── Three-qubit gates ───────────────────

    def cswap(self, q1: QubitInput, q2: QubitInput, q3: QubitInput) -> None:
        """Apply CSWAP (Fredkin) gate to three qubits.

        Args:
            q1: Control qubit - can be int, Qubit, or QRegSlice
            q2: First target qubit
            q3: Second target qubit
        """
        self.add_gate("CSWAP", [q1, q2, q3])

    def toffoli(self, q1: QubitInput, q2: QubitInput, q3: QubitInput) -> None:
        """Apply Toffoli (CCNOT) gate to three qubits.

        Args:
            q1: First control qubit
            q2: Second control qubit
            q3: Target qubit
        """
        self.add_gate("TOFFOLI", [q1, q2, q3])

    # ─────────────────── Parametric gates ───────────────────

    def u1(self, qn: QubitInput, lam: float = None, *, has_param: bool = False,
           trainable: bool = True, init_params: object = None) -> None:
        """Apply U1 single-parameter unitary gate."""
        self.add_gate("U1", qn, params=lam, has_param=has_param,
                       trainable=trainable, init_params=init_params)

    def u2(self, qn: QubitInput, phi: float = None, lam: float = None, *,
           has_param: bool = False, trainable: bool = True, init_params: object = None) -> None:
        """Apply U2 two-parameter unitary gate."""
        params = [phi, lam] if not has_param else None
        self.add_gate("U2", qn, params=params, has_param=has_param,
                       trainable=trainable, init_params=init_params)

    def u3(self, qn: QubitInput, theta: float = None, phi: float = None, lam: float = None, *,
           has_param: bool = False, trainable: bool = True, init_params: object = None) -> None:
        """Apply U3 three-parameter unitary gate."""
        params = [theta, phi, lam] if not has_param else None
        self.add_gate("U3", qn, params=params, has_param=has_param,
                       trainable=trainable, init_params=init_params)

    def xx(self, q1: QubitInput, q2: QubitInput, theta: float = None, *,
           has_param: bool = False, trainable: bool = True, init_params: object = None) -> None:
        """Apply XX Ising interaction gate."""
        self.add_gate("XX", [q1, q2], params=theta, has_param=has_param,
                       trainable=trainable, init_params=init_params)

    def yy(self, q1: QubitInput, q2: QubitInput, theta: float = None, *,
           has_param: bool = False, trainable: bool = True, init_params: object = None) -> None:
        """Apply YY Ising interaction gate."""
        self.add_gate("YY", [q1, q2], params=theta, has_param=has_param,
                       trainable=trainable, init_params=init_params)

    def zz(self, q1: QubitInput, q2: QubitInput, theta: float = None, *,
           has_param: bool = False, trainable: bool = True, init_params: object = None) -> None:
        """Apply ZZ Ising interaction gate."""
        self.add_gate("ZZ", [q1, q2], params=theta, has_param=has_param,
                       trainable=trainable, init_params=init_params)

    def xy(self, q1: QubitInput, q2: QubitInput, theta: float) -> None:
        """Apply XY Ising interaction gate.

        Args:
            q1: First qubit - can be int, Qubit, or QRegSlice
            q2: Second qubit - can be int, Qubit, or QRegSlice
            theta: Interaction angle in radians.
        """
        self.add_gate("XY", [q1, q2], params=theta)

    def phase2q(self, q1: QubitInput, q2: QubitInput, theta1: float, theta2: float, thetazz: float) -> None:
        """Apply two-qubit phase gate with local and ZZ terms.

        Args:
            q1: First qubit - can be int, Qubit, or QRegSlice
            q2: Second qubit - can be int, Qubit, or QRegSlice
            theta1: Local phase angle for q1 in radians.
            theta2: Local phase angle for q2 in radians.
            thetazz: ZZ interaction angle in radians.
        """
        self.add_gate("PHASE2Q", [q1, q2], params=[theta1, theta2, thetazz])

    def uu15(self, q1: QubitInput, q2: QubitInput, params: list[float]) -> None:
        """Apply general two-qubit UU15 gate with 15 parameters.

        Args:
            q1: First qubit - can be int, Qubit, or QRegSlice
            q2: Second qubit - can be int, Qubit, or QRegSlice
            params: List of 15 rotation parameters in radians.
        """
        self.add_gate("UU15", [q1, q2], params=params)

    def barrier(self, *qubits: QubitInput) -> None:
        """Insert a barrier across the specified qubits.

        Args:
            *qubits: Qubits to include in the barrier.
        """
        self.add_gate("BARRIER", list(qubits))

    def qram_declare(self, name: str, addr_size: int, data_size: int) -> None:
        """Declare a QRAM with the given address and data sizes.

        Args:
            name: Unique name for this QRAM.
            addr_size: Number of address qubits.
            data_size: Number of data qubits.
        """
        if name in self.qram_declarations:
            raise ValueError(f"QRAM '{name}' is already declared in this circuit.")
        self.qram_declarations[name] = (addr_size, data_size)

    def qram_call(self, name: str, *qubits: QubitInput) -> None:
        """Add a QRAM call to the circuit.

        Args:
            name: Name of a previously declared QRAM.
            *qubits: Qubit list (addr bits followed by data bits).
        """
        if name not in self.qram_declarations:
            raise ValueError(f"QRAM '{name}' has not been declared. Call qram_declare() first.")
        addr_size, data_size = self.qram_declarations[name]
        total = addr_size + data_size
        resolved = self._resolve_qubit(list(qubits))
        if isinstance(resolved, list) and len(resolved) != total:
            raise ValueError(
                f"QRAM '{name}' expects {total} qubits ({addr_size} addr + {data_size} data), "
                f"got {len(resolved)}."
            )
        self.add_gate(name, list(qubits))

    # ─────────────────── Measurement ───────────────────

    def measure(self, *qubits: QubitInput) -> None:
        """Schedule qubits for measurement.

        Each qubit may be measured **at most once** per circuit. Calling
        ``measure(0)`` and then ``measure(0)`` again — or passing the same
        qubit twice in a single call (``measure(0, 0)``) — raises
        ``ValueError``. This guards against the common mistake of using
        ``measure(0, 1)`` to measure two qubits when ``cbit`` is meant to be
        implicit; use one ``measure(q)`` call per qubit instead, or pass
        distinct qubit indices.

        Args:
            *qubits: One or more qubits to measure — can be int, Qubit, or QRegSlice.

        Raises:
            ValueError: Called inside an active CONTROL or DAGGER context
                block, or any qubit would be measured more than once.
        """
        if self._active_controls:
            raise ValueError("measure() cannot be called inside a control() context block.")
        if self._active_dagger:
            raise ValueError("measure() cannot be called inside a dagger() context block.")
        # Resolve all qubits to integers
        resolved_qubits = []
        for q in qubits:
            resolved = self._resolve_qubit(q)
            if isinstance(resolved, list):
                resolved_qubits.extend(resolved)
            else:
                resolved_qubits.append(resolved)

        # Reject duplicate measurements (within this call AND against any
        # previously-recorded measurements). This catches `measure(0, 0)`
        # and silent failures like `measure(0); measure(0)` that previously
        # accumulated into the measurement list.
        existing = set(self.measure_list or [])
        seen: set[int] = set()
        for q in resolved_qubits:
            if q in seen or q in existing:
                raise ValueError(
                    f"Qubit {q} is already measured in this circuit. "
                    f"Each qubit may be measured at most once. "
                    f"Did you mean `c.measure({q}); c.measure({q + 1})` "
                    f"instead of `c.measure({q}, {q})`?"
                )
            seen.add(q)

        self.record_qubit(resolved_qubits)
        if self.measure_list is None:
            self.measure_list = []
        self.measure_list.extend(resolved_qubits)
        self.cbit_num = len(self.measure_list)

    # ─────────────────── Control / Dagger context managers ───────────────────

    def control(self, *args: QubitInput) -> CircuitControlContext:
        """Return a context manager that wraps gates in a CONTROL block.

        All gates added inside the ``with`` block will be executed only
        when all specified control qubits are in state ``|1>``.

        Args:
            *args: One or more control qubits - can be int, Qubit, or QRegSlice

        Returns:
            A :class:`CircuitControlContext` context manager.

        Raises:
            ValueError: No control qubits were supplied.
        """
        # Resolve qubits to integers
        resolved = []
        for q in args:
            r = self._resolve_qubit(q)
            if isinstance(r, list):
                resolved.extend(r)
            else:
                resolved.append(r)
        self.record_qubit(resolved)
        if len(resolved) == 0:
            raise ValueError("Controller qubit must not be empty.")
        return CircuitControlContext(self, tuple(resolved))

    def set_control(self, *args: QubitInput) -> None:
        """Manually open a CONTROL block (low-level API; prefer :meth:`control`).

        Args:
            *args: Control qubits - can be int, Qubit, or QRegSlice
        """
        # Resolve qubits to integers
        resolved = []
        for q in args:
            r = self._resolve_qubit(q)
            if isinstance(r, list):
                resolved.extend(r)
            else:
                resolved.append(r)
        self.record_qubit(resolved)
        ret = "CONTROL "
        for q in resolved:
            ret += f"q[{q}], "
        self.circuit_str += ret[:-2] + "\n"
        # Update active-context state so add_gate picks up these controls.
        self._control_stack.append(tuple(resolved))
        self._active_controls = self._active_controls + resolved

    def unset_control(self) -> None:
        """Manually close a CONTROL block (low-level API; prefer :meth:`control`)."""
        self.circuit_str += "ENDCONTROL\n"
        if self._control_stack:
            popped = self._control_stack.pop()
            self._active_controls = self._active_controls[: len(self._active_controls) - len(popped)]

    def dagger(self) -> CircuitDagContext:
        """Return a context manager that wraps gates in a DAGGER block.

        All gates added inside the ``with`` block will be conjugate-transposed
        (adjoint).

        Returns:
            A :class:`CircuitDagContext` context manager.
        """
        return CircuitDagContext(self)

    def set_dagger(self) -> None:
        """Manually open a DAGGER block (low-level API; prefer :meth:`dagger`)."""
        self.circuit_str += "DAGGER\n"
        self._active_dagger = not self._active_dagger

    def unset_dagger(self) -> None:
        """Manually close a DAGGER block (low-level API; prefer :meth:`dagger`)."""
        self.circuit_str += "ENDDAGGER\n"
        self._active_dagger = not self._active_dagger

    # ─────────────────── Remapping ───────────────────

    def remapping(self, mapping: dict[int, int]) -> Circuit:
        """Create a new circuit with qubits remapped according to *mapping*."""
        if not all(isinstance(k, int) and isinstance(v, int) and k >= 0 and v >= 0 for k, v in mapping.items()):
            raise TypeError("All keys and values in mapping must be non-negative integers.")

        if len(set(mapping.values())) != len(mapping.values()):
            raise ValueError("A physical qubit is assigned more than once.")

        for qubit in self.used_qubit_list:
            if qubit not in mapping:
                raise ValueError(f"At least one qubit is not appeared in mapping. (qubit : {qubit})")

        unique_qubit_set: set[int] = set()
        for qubit in mapping:
            if qubit in unique_qubit_set:
                raise ValueError(f"Qubit is used twice in the mapping. Given mapping : ({mapping})")
            unique_qubit_set.add(qubit)

        c = deepcopy(self)

        def remap_opcode(opcode: OpCode, mp: dict[int, int]) -> OpCode:
            op_name, qubits, cbits, params, dagger, control_qubits = opcode
            new_qubits = [mp[q] for q in qubits] if isinstance(qubits, list) else mp[qubits]

            if control_qubits is not None:
                new_control_qubits = (
                    [mp[q] for q in control_qubits] if isinstance(control_qubits, list) else mp[control_qubits]
                )
            else:
                new_control_qubits = None

            return (op_name, new_qubits, cbits, params, dagger, new_control_qubits)

        c.opcode_list = [remap_opcode(op, mapping) for op in self.opcode_list]

        for i, old_qubit in enumerate(self.used_qubit_list):
            c.used_qubit_list[i] = mapping[old_qubit]

        for i, old_qubit in enumerate(self.measure_list):
            c.measure_list[i] = mapping[old_qubit]

        c.max_qubit = max(c.used_qubit_list)
        c.qubit_num = c.max_qubit + 1
        c.cbit_num = len(c.measure_list)

        return c
