"""Pauli string expectation value measurement via basis rotation."""

__all__ = ["pauli_expectation", "PauliExpectation", "pauli_expectation_example"]

from typing import Optional, List, Union

import numpy as np

from uniqc.circuit_builder import Circuit
from uniqc.simulator.qasm_simulator import QASM_Simulator


def _parity(bitstring: str, pauli_string: str) -> int:
    """Compute parity contribution of a measurement outcome for a Pauli string.

    Note: bitstring uses big-endian convention (MSB first) matching the
    measurement output format where q[0] corresponds to the rightmost bit.
    Pauli string is reversed to align with this convention.

    For each qubit i:
      Z → contributes 1 if bit[i] == '1'
      X → contributes 1 if bit[i] == '1'
      Y → contributes 1 if bit[i] == '1'
    The total parity is the XOR (sum mod 2) of all contributions.
    Returns 0 for even parity (+1 eigenvalue) or 1 for odd parity (-1 eigenvalue).
    """
    parity = 0
    # Reverse pauli_string to match big-endian bitstring convention
    # where pauli_string[0] corresponds to qubit 0 (rightmost bit)
    for pauli, bit in zip(reversed(pauli_string), bitstring):
        if bit == '1' and pauli.upper() in ('Z', 'X', 'Y'):
            parity ^= 1
    return parity


def _apply_basis_rotation(circuit: Circuit, pauli_string: str) -> Circuit:
    """Add basis-rotation gates to a circuit copy for measuring a Pauli string.

    For each qubit i with pauli_string[i]:
      Z → no rotation
      X → H gate
      Y → Sdag then H (equivalently, Sdg-H sequence)
      I → no rotation
    """
    rot_circuit = circuit.copy()
    for i, pauli in enumerate(pauli_string):
        p = pauli.upper()
        if p == 'X':
            rot_circuit.h(i)
        elif p == 'Y':
            rot_circuit.sdg(i)
            rot_circuit.h(i)
        # Z and I: no rotation needed
    return rot_circuit


def _statevector_expectation(circuit: Circuit, pauli_string: str) -> float:
    """Compute the exact ⟨pauli_string⟩ expectation from the statevector.

    Applies basis-rotation gates to rotate to the measurement basis, then
    computes the expectation analytically from the final statevector.
    """
    rot_circuit = _apply_basis_rotation(circuit, pauli_string)
    n = rot_circuit.max_qubit + 1

    # Use QASM simulator in statevector mode
    sim = QASM_Simulator(backend_type='statevector', n_qubits=n)
    qasm = rot_circuit.qasm
    result = sim.simulate_statevector(qasm)

    # result is a list of complex amplitudes, convert to probabilities
    probs = np.abs(result) ** 2
    exp_val = 0.0
    for idx, p in enumerate(probs):
        # Build bitstring for this index (big-endian: qubit 0 is MSB)
        bitstring = format(idx, f'0{n}b')
        parity = _parity(bitstring, pauli_string.upper())
        if parity == 0:
            exp_val += p
        else:
            exp_val -= p
    return float(exp_val)


def _shots_expectation(circuit: Circuit, pauli_string: str, shots: int) -> float:
    """Estimate ⟨pauli_string⟩ via basis rotation + shots on QASM simulator."""
    rot_circuit = _apply_basis_rotation(circuit, pauli_string)
    n = rot_circuit.max_qubit + 1

    sim = QASM_Simulator(backend_type='statevector', n_qubits=n)
    qasm = rot_circuit.qasm
    counts = sim.simulate_shots(qasm, shots=shots)
    total = sum(counts.values())

    exp_val = 0.0
    for bitstring_int, count in counts.items():
        # Convert int to bitstring and pad to n qubits
        bitstring = format(bitstring_int, f'0{n}b')
        parity = _parity(bitstring, pauli_string.upper())
        p = count / total
        if parity == 0:
            exp_val += p
        else:
            exp_val -= p
    return float(exp_val)


def _normalize_pauli_string(
    pauli_spec: Union[str, List[tuple]],
    n_qubits: int,
) -> str:
    """Normalize the various supported Pauli-string formats to compact form.

    Accepted inputs:

    - **Compact string** (``len == n_qubits``): ``"ZIZ"``, ``"XYZ"``, ``"IZI"`` —
      ``pauli_spec[i]`` is the operator on qubit ``i`` (left-to-right).
    - **Indexed string**: ``"Z0Z1"``, ``"X0Y2"`` — operator-index pairs; any
      qubit not listed is treated as identity.  Indices may appear in any
      order but must be in ``[0, n_qubits)``.
    - **List of tuples**: ``[("Z", 0), ("Z", 1)]`` — same semantics as the
      indexed-string form.

    Returns the compact-string representation (length exactly ``n_qubits``,
    upper-cased, characters in ``"IXYZ"``).

    Raises:
        ValueError: If ``pauli_spec`` is malformed, contains invalid Pauli
            characters, or addresses qubit indices outside ``[0, n_qubits)``.
    """
    import re as _re

    # Form 3: list[tuple[str, int]]
    if isinstance(pauli_spec, list):
        out = ["I"] * n_qubits
        for item in pauli_spec:
            if not (isinstance(item, tuple) and len(item) == 2):
                raise ValueError(
                    "pauli_string list entries must be (Pauli, qubit) tuples, "
                    f"got: {item!r}"
                )
            op, idx = item
            op = str(op).upper()
            if op not in ("I", "X", "Y", "Z"):
                raise ValueError(f"pauli_string contains invalid operator: {op!r}")
            if not isinstance(idx, int) or idx < 0 or idx >= n_qubits:
                raise ValueError(
                    f"pauli_string qubit index out of range [0, {n_qubits}): {idx!r}"
                )
            out[idx] = op
        return "".join(out)

    if not isinstance(pauli_spec, str):
        raise ValueError(
            f"pauli_string must be a str or list[(op, qubit)], got: {type(pauli_spec).__name__}"
        )

    upper = pauli_spec.upper().replace(" ", "")

    # Form 2: indexed string like "Z0Z1" / "X0Y2"
    if _re.fullmatch(r"([IXYZ]\d+)+", upper):
        out = ["I"] * n_qubits
        for op, idx_str in _re.findall(r"([IXYZ])(\d+)", upper):
            idx = int(idx_str)
            if idx < 0 or idx >= n_qubits:
                raise ValueError(
                    f"pauli_string qubit index out of range [0, {n_qubits}): {idx}"
                )
            out[idx] = op
        return "".join(out)

    # Form 1: compact string
    if len(upper) != n_qubits:
        raise ValueError(
            f"pauli_string length ({len(upper)}) must match circuit n_qubits "
            f"({n_qubits}), or use indexed form like 'Z0Z1' / [('Z', 0), ('Z', 1)]"
        )
    for ch in upper:
        if ch not in ("I", "X", "Y", "Z"):
            raise ValueError(
                f"pauli_string must contain only I/X/Y/Z, got: {pauli_spec!r}"
            )
    return upper


def pauli_expectation(
    circuit: Circuit,
    pauli_string: Union[str, List[tuple]],
    shots: Optional[int] = None,
) -> float:
    """Measure the expectation value of a Pauli string on a circuit.

    For each qubit i, the measurement basis is determined by the operator
    assigned to that qubit:

    - ``'I'``: trace out (identity, contributes trivially)
    - ``'Z'``: measure in the computational (Z) basis — no rotation needed
    - ``'X'``: apply Hadamard before Z measurement
    - ``'Y'``: apply Sdag then Hadamard before Z measurement

    When ``shots`` is ``None``, the statevector simulator is used to compute
    the exact expectation analytically.  When ``shots`` is given, the circuit
    is simulated ``shots`` times and the empirical frequency is used.

    Args:
        circuit: Quantum circuit. Must contain only gates supported by
            ``QASM_Simulator`` and end with measurement instructions.
        pauli_string: Pauli string in any of three accepted forms (case-
            insensitive):

            - **Compact** (length == n_qubits): ``"XYZ"``, ``"IZI"``.
            - **Indexed** (``"Z0Z1"``): operator-index pairs; any qubit not
              listed is identity. Matches the convention of
              :func:`uniqc.algorithms.core.ansatz.qaoa_ansatz.cost_hamiltonian`.
            - **Tuple list**: ``[("Z", 0), ("Z", 1)]`` — same semantics as
              the indexed form.
        shots: Number of measurement shots. ``None`` uses statevector mode
            for the exact analytical value.

    Returns:
        Expectation value ⟨psi|P|psi⟩ as a float in the interval ``[-1, 1]``.

    Raises:
        ValueError: ``pauli_string`` is malformed, contains invalid characters,
            or its length / qubit indices do not fit the circuit.
        ValueError: ``shots`` is not a positive integer.

    Example:
        >>> from uniqc.circuit_builder import Circuit
        >>> from uniqc.algorithms.core.measurement import pauli_expectation
        >>> c = Circuit()
        >>> c.h(0)
        >>> c.cx(0, 1)          # Bell state (|00⟩+|11⟩)/√2
        >>> c.measure(0, 1)
        >>> pauli_expectation(c, "ZZ")               # compact form
        1.0
        >>> pauli_expectation(c, "Z0Z1")             # indexed form
        1.0
        >>> pauli_expectation(c, [("Z", 0), ("Z", 1)])  # tuple-list form
        1.0
    """
    n_qubits = circuit.max_qubit + 1
    pauli_upper = _normalize_pauli_string(pauli_string, n_qubits)

    if shots is not None:
        if not isinstance(shots, int) or shots <= 0:
            raise ValueError(f"shots must be a positive integer, got: {shots}")
        return _shots_expectation(circuit, pauli_upper, shots)

    return _statevector_expectation(circuit, pauli_upper)


class PauliExpectation:
    """Class-based interface for Pauli-string expectation measurement.

    Convention: the constructor accepts a *clean* state-preparation
    :class:`Circuit` (no measurement instructions). The class adds basis
    rotations and measurements internally; the input circuit is **not**
    mutated.

    Example::

        from uniqc.circuit_builder import Circuit
        from uniqc.algorithms.core.measurement import PauliExpectation

        c = Circuit()
        c.h(0); c.cx(0, 1)
        meas = PauliExpectation(c, "ZZ", shots=10000)
        readouts = meas.get_readout_circuits()    # list[Circuit]
        value = meas.execute("statevector")        # float in [-1, 1]
    """

    def __init__(
        self,
        circuit: Circuit,
        pauli_string: Union[str, List[tuple]],
        shots: Optional[int] = None,
    ) -> None:
        n_qubits = circuit.max_qubit + 1
        pauli_upper = _normalize_pauli_string(pauli_string, n_qubits)
        if shots is not None and (not isinstance(shots, int) or shots <= 0):
            raise ValueError(f"shots must be a positive integer, got: {shots}")
        self.circuit = circuit.copy()
        self.pauli_string = pauli_upper
        self.shots = shots

    def get_readout_circuits(self) -> List[Circuit]:
        """Return the list of readout circuits (one per measurement basis).

        For a single Pauli string this returns a one-element list containing
        the basis-rotated, measured circuit.
        """
        rot = _apply_basis_rotation(self.circuit, self.pauli_string)
        n = rot.max_qubit + 1
        for q in range(n):
            rot.measure(q)
        return [rot]

    def execute(
        self,
        backend: Union[str, "object"] = "statevector",
        *,
        program_type: str = "qasm",
        **kwargs,
    ) -> float:
        """Execute the readout circuits and return the expectation value.

        Args:
            backend: Either a backend-type name (string, e.g. ``"statevector"``)
                or a pre-built simulator object exposing ``simulate_statevector``
                / ``simulate_shots``.
            program_type: Currently only ``"qasm"`` is supported.
            **kwargs: Forwarded to simulator construction when *backend* is a
                string.
        """
        if program_type != "qasm":
            raise ValueError(
                f"PauliExpectation currently supports program_type='qasm' only, "
                f"got {program_type!r}"
            )
        if self.shots is None:
            return _statevector_expectation(self.circuit, self.pauli_string)
        return _shots_expectation(self.circuit, self.pauli_string, self.shots)


def pauli_expectation_example() -> float:
    """Tiny PauliExpectation demo that returns ⟨ZZ⟩ on a Bell state (≈ 1.0)."""
    c = Circuit()
    c.h(0)
    c.cx(0, 1)
    return PauliExpectation(c, "ZZ").execute("statevector")
