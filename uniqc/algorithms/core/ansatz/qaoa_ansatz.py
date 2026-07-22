"""QAOA (Quantum Approximate Optimization Algorithm) ansatz.

Constructs the alternating-operator ansatz used in QAOA for solving
combinatorial optimisation problems.
"""

__all__ = ["qaoa_ansatz"]

from typing import TYPE_CHECKING, Optional, Union

import numpy as np

from uniqc._error_hints import format_enriched_message
from uniqc.circuit_builder import Circuit

from ._pauli_unitary import _apply_cost_unitary, _parse_pauli_string

if TYPE_CHECKING:
    from uniqc.circuit_builder.parameter import Parameters


def _apply_mixer_unitary(
    circuit: Circuit,
    n_qubits: int,
    qubits: list[int],
    beta: float,
) -> None:
    """Apply the mixer unitary exp(-i β Σ X_i) = Π Rx(2β)."""
    for q in qubits:
        circuit.h(q)
        if abs(2 * beta) > 1e-15:
            circuit.rz(q, float(2 * beta))
        circuit.h(q)


def qaoa_ansatz(
    cost_hamiltonian: list[tuple[str, float]],
    p: int = 1,
    qubits: list[int] | None = None,
    betas: Union["Parameters", np.ndarray] | None = None,
    gammas: Union["Parameters", np.ndarray] | None = None,
    *,
    mixer: str = "x",
    initial_state: Optional["Circuit"] = None,
    multi_angle: bool = False,
) -> Circuit:
    """Build a QAOA ansatz circuit.

    The ansatz alternates between the cost unitary
    :math:`U_C(\\gamma) = e^{-i\\gamma H_C}` and the mixer unitary
    :math:`U_M(\\beta)` for *p* layers.

    Args:
        cost_hamiltonian: List of ``(pauli_string, coefficient)`` tuples.
            Pauli strings use the format ``"Z0Z1"``, ``"X0Y1Z2"``, etc.
        p: Number of QAOA layers.
        qubits: Qubit indices.  ``None`` → auto-detect from hamiltonian.
        betas: Mixer angles, length *p*.  ``None`` → random.
        gammas: Cost angles, length *p*.  ``None`` → random.
        mixer: Mixer type. Options:
            - ``"x"``: Standard X mixer: :math:`\\sum X_i` (default)
            - ``"xy"``: XY mixer for constrained optimization
        initial_state: Custom initial state circuit.  ``None`` → uniform superposition (Hadamards).
        multi_angle: If ``True``, use MA-QAOA: each Pauli term gets its own gamma
            and each qubit gets its own beta. Overrides *betas* and *gammas*.

    Returns:
        A :class:`Circuit` object.

    Raises:
        ValueError: Angle arrays have wrong length.

    Example:
        >>> from uniqc.algorithms.core.ansatz import qaoa_ansatz
        >>> H = [("Z0Z1", 1.0), ("Z1Z2", 1.0), ("Z0Z2", 0.5)]
        >>> c = qaoa_ansatz(H, p=2)

        XY mixer for constrained optimization:
        >>> c = qaoa_ansatz(H, p=2, mixer="xy")

        Warm-start with custom initial state:
        >>> from uniqc.circuit_builder import Circuit
        >>> init = Circuit()
        >>> init.x(0)  # custom initial state
        >>> c = qaoa_ansatz(H, p=2, initial_state=init)
    """
    # Determine qubit set
    all_qubits = set()
    for pauli_str, _ in cost_hamiltonian:
        for _, q in _parse_pauli_string(pauli_str):
            all_qubits.add(q)
    n_qubits = max(all_qubits) + 1 if all_qubits else 0

    qubits = list(range(n_qubits)) if qubits is None else list(qubits)

    n_terms = len(cost_hamiltonian)

    # Import Parameters for auto-generation
    from uniqc.circuit_builder.parameter import Parameters as ParamClass

    def _validate_and_convert_params(
        params: ParamClass | np.ndarray | None,
        expected_len: int,
        name: str,
    ) -> ParamClass:
        """Validate and convert params to Parameters object."""
        if params is None:
            # Auto-generate named Parameters
            p_obj = ParamClass(f"{name}_qaoa", size=expected_len)
            rng = np.random.default_rng(0)
            p_obj.bind(list(rng.uniform(0, np.pi, size=expected_len)))
            return p_obj
        elif isinstance(params, ParamClass):
            if len(params) != expected_len:
                raise ValueError(
                    format_enriched_message(
                        f"{name} requires {expected_len} parameters, got {len(params)}",
                        "circuit_validation",
                    )
                )
            if not params[0].is_bound:
                rng = np.random.default_rng(0)
                params.bind(list(rng.uniform(0, np.pi, size=expected_len)))
            return params
        else:
            # Convert np.ndarray to Parameters
            params_arr = np.asarray(params)
            if len(params_arr) != expected_len:
                raise ValueError(
                    format_enriched_message(
                        f"{name} requires {expected_len} parameters, got {len(params_arr)}",
                        "circuit_validation",
                    )
                )
            p_obj = ParamClass(f"{name}_qaoa", size=expected_len)
            p_obj.bind(list(params_arr.flatten()))
            return p_obj

    # Handle multi-angle QAOA (MA-QAOA)
    if multi_angle:
        total_gammas = n_terms * p
        total_betas = n_qubits * p
        gammas = _validate_and_convert_params(gammas, total_gammas, "gammas")
        betas = _validate_and_convert_params(betas, total_betas, "betas")
    else:
        # Standard QAOA
        gammas = _validate_and_convert_params(gammas, p, "gammas")
        betas = _validate_and_convert_params(betas, p, "betas")

    circuit = Circuit()

    # Initial state
    if initial_state is not None:
        circuit.add_circuit(initial_state)
    else:
        for q in qubits:
            circuit.h(q)

    # QAOA layers
    for layer in range(p):
        if multi_angle:
            # MA-QAOA: cost unitary with per-term gammas
            for t, (pauli_str, coeff) in enumerate(cost_hamiltonian):
                gamma = gammas[layer * n_terms + t].evaluate()
                _apply_cost_unitary(circuit, [(pauli_str, coeff)], gamma)
            # MA-QAOA: mixer with per-qubit betas
            for i, q in enumerate(qubits):
                beta = betas[layer * n_qubits + i].evaluate()
                circuit.h(q)
                if abs(2 * beta) > 1e-15:
                    circuit.rz(q, float(2 * beta))
                circuit.h(q)
        else:
            # Standard QAOA
            _apply_cost_unitary(circuit, cost_hamiltonian, gammas[layer].evaluate())
            if mixer == "xy":
                _apply_xy_mixer(circuit, qubits, betas[layer].evaluate())
            else:
                _apply_mixer_unitary(circuit, n_qubits, qubits, betas[layer].evaluate())

    # Attach parameters to circuit for traceability
    circuit._params = {"betas": betas, "gammas": gammas}

    return circuit


def _apply_xy_mixer(
    circuit: Circuit,
    qubits: list[int],
    beta: float,
) -> None:
    """Apply the XY mixer: exp(-i β Σ_{i} (XX_i,i+1 + YY_i,i+1)).

    For each adjacent pair (i, i+1), applies Rxx(2β) + Ryy(2β).
    This preserves the number of excitations, useful for constrained optimization.
    """
    if abs(beta) < 1e-15:
        return

    for i in range(len(qubits) - 1):
        u, v = qubits[i], qubits[i + 1]
        # Rxx(2β)
        if abs(2 * beta) > 1e-15:
            circuit.xx(u, v, float(2 * beta))
        # Ryy(2β)
        if abs(2 * beta) > 1e-15:
            circuit.yy(u, v, float(2 * beta))
