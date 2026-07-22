"""Arbitrary complex state preparation lowered to ``U3`` and ``CNOT``."""

from __future__ import annotations

__all__ = ["rotation_prepare"]

import numpy as np

from uniqc._error_hints import format_enriched_message
from uniqc.circuit_builder import Circuit


def rotation_prepare(
    circuit: Circuit,
    target_vector: np.ndarray,
    qubits: list[int] | None = None,
) -> None:
    """Prepare an arbitrary normalized complex state on ``qubits``.

    The target vector is completed to a unitary matrix whose first column is
    the desired state. Qiskit's maintained unitary synthesis lowers it to the
    stable ``U3``/``CNOT`` basis, which is then remapped onto the requested
    physical qubit indices. Qiskit and SciPy are core UnifiedQuantum
    dependencies, so this path has the same availability as the package.

    Args:
        circuit: Circuit to modify in place.
        target_vector: One-dimensional complex amplitude vector of length
            ``2**n``. It is normalized automatically.
        qubits: Distinct target qubit indices. ``None`` uses ``range(n)``.

    Raises:
        ValueError: The vector is empty, zero, not one-dimensional, not a
            power-of-two length, or the qubit mapping is invalid.
    """
    target = np.asarray(target_vector, dtype=np.complex128)
    if target.ndim != 1 or target.size == 0:
        raise ValueError(
            format_enriched_message(
                "target_vector must be a non-empty one-dimensional array",
                "circuit_validation",
            )
        )

    n_qubits = int(round(np.log2(target.size)))
    if 2**n_qubits != target.size:
        raise ValueError(
            format_enriched_message(
                f"target_vector length ({target.size}) must be a power of 2",
                "circuit_validation",
            )
        )

    norm = np.linalg.norm(target)
    if norm < 1e-15:
        raise ValueError(
            format_enriched_message(
                "target_vector must not be the zero vector",
                "circuit_validation",
            )
        )
    target = target / norm

    mapped_qubits = list(range(n_qubits)) if qubits is None else [int(qubit) for qubit in qubits]
    if len(mapped_qubits) != n_qubits:
        raise ValueError(
            format_enriched_message(
                f"Expected {n_qubits} target qubits, got {len(mapped_qubits)}",
                "circuit_validation",
            )
        )
    if len(set(mapped_qubits)) != len(mapped_qubits) or any(qubit < 0 for qubit in mapped_qubits):
        raise ValueError(
            format_enriched_message(
                "qubits must contain distinct non-negative indices",
                "circuit_validation",
            )
        )

    if n_qubits == 0:
        return

    # Preserve the requested register width even when synthesis omits idle
    # leading qubits (for example, preparing |00...0>).
    for qubit in mapped_qubits:
        circuit.identity(qubit)

    from qiskit import QuantumCircuit, transpile
    from qiskit.circuit.library import UnitaryGate
    from scipy.linalg import null_space

    qiskit_circuit = QuantumCircuit(n_qubits)
    complement = null_space(target.conj().reshape(1, -1))
    unitary = np.column_stack([target, complement])
    qiskit_circuit.append(UnitaryGate(unitary), range(n_qubits))
    lowered = transpile(
        qiskit_circuit,
        basis_gates=["u3", "cx"],
        optimization_level=0,
    )

    for instruction in lowered.data:
        name = instruction.operation.name.lower()
        logical_qubits = [lowered.find_bit(qubit).index for qubit in instruction.qubits]
        physical_qubits = [mapped_qubits[index] for index in logical_qubits]
        if name == "u3":
            theta, phi, lam = [float(param) for param in instruction.operation.params]
            circuit.u3(physical_qubits[0], theta, phi, lam)
        elif name == "cx":
            circuit.cnot(physical_qubits[0], physical_qubits[1])
        elif name != "barrier":
            raise RuntimeError(f"Unexpected state-preparation basis gate: {name!r}")
