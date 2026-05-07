"""Basis-rotation measurement for arbitrary single-qubit measurement bases."""

__all__ = ["basis_rotation_measurement"]

from typing import Optional, List, Union, Dict
import numpy as np

from uniqc.circuit_builder import Circuit
from uniqc.simulator.qasm_simulator import QASM_Simulator


def basis_rotation_measurement(
    circuit: Circuit,
    qubits: Optional[List[int]] = None,
    basis: Optional[Union[str, List[str]]] = None,
    shots: Optional[int] = None,
) -> Union[Dict[str, float], List[float]]:
    """Measure a circuit by applying basis-rotation gates and then
    measuring in the computational (Z) basis.

    For each qubit, the rotation applied before measurement is determined
    by the corresponding entry in ``basis``:

    - ``"Z"`` — no rotation (Z basis, default)
    - ``"X"`` — Hadamard gate (H), measures X basis
    - ``"Y"`` — ``S^dagger H``, measures Y basis
    - ``"I"`` — no rotation (Z basis, identity)

    When ``shots`` is ``None``, the statevector simulator is used to return
    the exact probability distribution.  When ``shots`` is given, the
    distribution is estimated from that many samples.

    Args:
        circuit: Quantum circuit (must contain MEASURE instructions).
        qubits: Indices of qubits to include.  ``None`` means all qubits.
        basis: Per-qubit measurement basis.  Accepts a single string such as
            ``"XYZ"`` (applied left-to-right to ``qubits``, with each
            character one of ``"I"`` / ``"X"`` / ``"Y"`` / ``"Z"``), a list
            of strings such as ``["X", "Y", "Z"]``, or ``None`` (default,
            Z basis for all qubits).
        shots: Number of measurement shots.  ``None`` returns the exact
            probability vector from the statevector simulator.

    Returns:
        When ``shots`` is ``None``, a ``dict`` mapping each computational-basis
        outcome string (e.g. ``"01"``) to its probability.  When ``shots`` is
        given, a ``dict`` mapping outcome strings to integer counts
        (frequency).

    Raises:
        ValueError: ``len(basis)`` does not match ``len(qubits)``.

        ValueError: ``shots`` is not a positive integer.

        ValueError: ``basis`` contains invalid characters.

    Example:
        >>> from uniqc.circuit_builder import Circuit
        >>> from uniqc.algorithms.core.measurement import basis_rotation_measurement
        >>> c = Circuit()
        >>> c.h(0)           # |0⟩ → (|0⟩+|1⟩)/√2
        >>> c.cx(0, 1)       # Bell state (|00⟩+|11⟩)/√2
        >>> c.measure(0, 1)
        >>> # Measure qubit 0 in X basis, qubit 1 in Z basis
        >>> probs = basis_rotation_measurement(c, basis="XZ")
        >>> abs(probs["00"] - 0.5) < 1e-6   # P(0) in X basis for |+⟩ is 0.5
        True
    """
    n_qubits = circuit.max_qubit + 1

    # Guard: this implementation injects basis-rotation gates immediately
    # before existing MEASURE instructions in the circuit's QASM. If the
    # caller has not already added MEASURE instructions, no rotations are
    # applied and the result will silently fall back to the Z-basis
    # distribution — which is **wrong** for X/Y measurements. Catch that
    # here so users get an actionable error instead of bad numbers.
    if not getattr(circuit, "measure_list", None):
        raise ValueError(
            "basis_rotation_measurement requires the circuit to already contain "
            "MEASURE instructions (e.g. `circuit.measure(*qubits)`); "
            "without them, basis rotations cannot be injected and the "
            "returned distribution would silently be wrong for X/Y bases."
        )

    if qubits is None:
        qubits = list(range(n_qubits))
    else:
        qubits = list(qubits)

    n = len(qubits)

    # Parse basis argument
    if basis is None:
        basis_strs: list[str] = ["Z"] * n
    elif isinstance(basis, str):
        basis_strs = list(basis.upper())
        if len(basis_strs) != n:
            raise ValueError(
                f"basis string length ({len(basis_strs)}) must match "
                f"len(qubits) ({n})"
            )
    elif isinstance(basis, list):
        if len(basis) != n:
            raise ValueError(
                f"len(basis) ({len(basis)}) must match len(qubits) ({n})"
            )
        basis_strs = [b.upper() for b in basis]
    else:
        raise TypeError(f"basis must be str, list, or None, got {type(basis).__name__}")

    for b in basis_strs:
        if b not in ("I", "X", "Y", "Z"):
            raise ValueError(
                f"basis must only contain I/X/Y/Z, got: {b!r}"
            )

    if shots is not None and (not isinstance(shots, int) or shots <= 0):
        raise ValueError(f"shots must be a positive integer, got {shots}")

    # Build rotation gate injection map per qubit index
    rot_gates: dict[int, list[str]] = {i: [] for i in range(n)}
    for i, b in enumerate(basis_strs):
        if b == "X":
            rot_gates[i].append(f"h q[{i}];")
        elif b == "Y":
            # Sdg then H maps Y eigenstates → Z eigenstates
            rot_gates[i].append(f"sdg q[{i}];")
            rot_gates[i].append(f"h q[{i}];")

    # Inject rotations before each MEASURE line
    lines = circuit.qasm.splitlines()
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("measure "):
            left = stripped.split("->")[0].strip()
            qi = int(left.split("[")[1].split("]")[0])
            for gate in rot_gates[qi]:
                new_lines.append(gate)
        new_lines.append(line)

    modified_qasm = "\n".join(new_lines)

    # Simulate
    sim = QASM_Simulator(least_qubit_remapping=False)
    if shots is None:
        probs = sim.simulate_pmeasure(modified_qasm)
        return {f"{i:0{n}b}": float(p) for i, p in enumerate(probs)}
    else:
        counts = sim.simulate_shots(modified_qasm, shots=shots)
        return {f"{k:0{n}b}": v for k, v in counts.items()}


__all__ = list(set(globals().get("__all__", []) + [
    "basis_rotation_measurement",
    "BasisRotationMeasurement", "basis_rotation_measurement_example",
]))


class BasisRotationMeasurement:
    """Class-based interface for single-/multi-basis rotation measurement."""

    def __init__(
        self,
        circuit: Circuit,
        qubits: Optional[List[int]] = None,
        basis: Optional[Union[str, List[str]]] = None,
        shots: Optional[int] = None,
    ) -> None:
        self.circuit = circuit.copy()
        self.qubits = qubits
        self.basis = basis
        self.shots = shots

    def get_readout_circuits(self) -> List[Circuit]:
        """Return the basis-rotated, measured circuit(s).

        For a single-basis measurement returns a one-element list.
        """
        rot = self.circuit.copy()
        n = rot.max_qubit + 1
        basis = self.basis
        if isinstance(basis, str):
            basis = list(basis)
        if basis is None:
            basis = ["Z"] * n
        for i, b in enumerate(basis):
            if b == "X":
                rot.h(i)
            elif b == "Y":
                rot.sdg(i)
                rot.h(i)
        for q in range(n):
            rot.measure(q)
        return [rot]

    def execute(self, backend="statevector", *, program_type="qasm", **kwargs):
        """Run the measurement and return the existing function's output."""
        measured = self.circuit.copy()
        n = measured.max_qubit + 1
        for q in range(n):
            measured.measure(q)
        return basis_rotation_measurement(
            measured, qubits=self.qubits, basis=self.basis, shots=self.shots
        )


def basis_rotation_measurement_example():
    """Tiny example: measure a |+⟩ state in the X basis."""
    c = Circuit()
    c.h(0)
    return BasisRotationMeasurement(c, basis="X", shots=1024).execute()
