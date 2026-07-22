"""Hardware-Efficient Ansatz (HEA).

Generates a parameterised circuit with configurable single-qubit rotations,
entangling gates, and entanglement topologies, suitable for NISQ devices.
"""

__all__ = ["hea", "hea_param_count"]

from collections.abc import Callable
from typing import TYPE_CHECKING, Optional, Union

import numpy as np

from uniqc._error_hints import format_enriched_message
from uniqc.circuit_builder import Circuit

if TYPE_CHECKING:
    from uniqc.circuit_builder.parameter import Parameters

from ._hardware_aware import select_ansatz_config
from ._topology import count_edges_per_layer, generate_edges
from ._types import EntanglementTopology, EntanglingGate, RotationGate

if TYPE_CHECKING:
    from uniqc.backend_adapter.backend_info import BackendInfo


# Default configuration (reproduces original HEA behavior)
_DEFAULT_ROTATION_GATES = [RotationGate.RZ, RotationGate.RY]
_DEFAULT_ENTANGLING_GATE = EntanglingGate.CNOT
_DEFAULT_TOPOLOGY = EntanglementTopology.RING

# Entangling gate dispatch: maps enum to Circuit method
_ENTANGLING_DISPATCH: dict[EntanglingGate, Callable[[Circuit, int, int, float], None]] = {
    EntanglingGate.CNOT: lambda c, u, v, _: c.cx(u, v),
    EntanglingGate.CZ: lambda c, u, v, _: c.cz(u, v),
    EntanglingGate.ISWAP: lambda c, u, v, _: c.iswap(u, v),
    EntanglingGate.CRX: lambda c, u, v, θ: c.crx(u, v, θ),
    EntanglingGate.CRY: lambda c, u, v, θ: c.cry(u, v, θ),
    EntanglingGate.CRZ: lambda c, u, v, θ: c.crz(u, v, θ),
    EntanglingGate.XX: lambda c, u, v, θ: c.xx(u, v, θ),
    EntanglingGate.YY: lambda c, u, v, θ: c.yy(u, v, θ),
    EntanglingGate.ZZ: lambda c, u, v, θ: c.zz(u, v, θ),
}


def _normalize_rotation_gates(
    gates: list[str | RotationGate] | None,
) -> list[RotationGate]:
    """Normalize rotation gate input to list of RotationGate enums."""
    if gates is None:
        return _DEFAULT_ROTATION_GATES.copy()

    normalized = []
    for g in gates:
        if isinstance(g, RotationGate):
            normalized.append(g)
        elif isinstance(g, str):
            try:
                normalized.append(RotationGate(g.lower()))
            except ValueError as exc:
                raise ValueError(
                    format_enriched_message(
                        f"Unknown rotation gate: {g!r}. Valid: {[e.value for e in RotationGate]}",
                        "circuit_validation",
                    )
                ) from exc
        else:
            raise ValueError(
                format_enriched_message(
                    f"rotation_gates must be strings or RotationGate, got {type(g)}",
                    "circuit_validation",
                )
            )
    return normalized


def _normalize_entangling_gate(
    gate: str | EntanglingGate | None,
) -> EntanglingGate:
    """Normalize entangling gate input to EntanglingGate enum."""
    if gate is None:
        return _DEFAULT_ENTANGLING_GATE

    if isinstance(gate, EntanglingGate):
        return gate
    if isinstance(gate, str):
        try:
            return EntanglingGate(gate.lower())
        except ValueError as exc:
            raise ValueError(
                format_enriched_message(
                    f"Unknown entangling gate: {gate!r}. Valid: {[e.value for e in EntanglingGate]}",
                    "circuit_validation",
                )
            ) from exc
    raise ValueError(
        format_enriched_message(
            f"entangling_gate must be a string or EntanglingGate, got {type(gate)}",
            "circuit_validation",
        )
    )


def _normalize_topology(
    topology: str | EntanglementTopology | None,
) -> EntanglementTopology:
    """Normalize topology input to EntanglementTopology enum."""
    if topology is None:
        return _DEFAULT_TOPOLOGY

    if isinstance(topology, EntanglementTopology):
        return topology
    if isinstance(topology, str):
        try:
            return EntanglementTopology(topology.lower())
        except ValueError as exc:
            raise ValueError(
                format_enriched_message(
                    f"Unknown topology: {topology!r}. Valid: {[e.value for e in EntanglementTopology]}",
                    "circuit_validation",
                )
            ) from exc
    raise ValueError(
        format_enriched_message(
            f"topology must be a string or EntanglementTopology, got {type(topology)}",
            "circuit_validation",
        )
    )


def hea_param_count(
    n_qubits: int,
    depth: int = 1,
    *,
    qubits: list[int] | None = None,
    rotation_gates: list[str | RotationGate] | None = None,
    entangling_gate: str | EntanglingGate | None = None,
    topology: str | EntanglementTopology | None = None,
    custom_edges: list[tuple[int, int]] | None = None,
    backend_info: Optional["BackendInfo"] = None,
) -> int:
    """Calculate the number of parameters required for an HEA circuit.

    Use this to determine the parameter array size before building the circuit.

    Args:
        n_qubits: Number of qubits.
        depth: Number of ansatz layers.
        qubits: Qubit indices.  ``None`` → ``list(range(n_qubits))``.
        rotation_gates: List of rotation gate types per qubit per layer.
        entangling_gate: Type of entangling gate.
        topology: Entanglement topology type.
        custom_edges: Required for CUSTOM topology.
        backend_info: Backend info for auto-configuration.

    Returns:
        Total number of parameters required.
    """
    qubits = list(range(n_qubits)) if qubits is None else list(qubits)

    # Handle auto-config from backend_info
    if backend_info is not None:
        topo, gate, edges = select_ansatz_config(backend_info, n_qubits)
        if topology is None:
            topology = topo
        if entangling_gate is None:
            entangling_gate = gate
        if custom_edges is None:
            custom_edges = edges

    rot_gates = _normalize_rotation_gates(rotation_gates)
    ent_gate = _normalize_entangling_gate(entangling_gate)
    topo = _normalize_topology(topology)

    # Rotation parameters: len(rotation_gates) * n_qubits * depth
    rot_params = len(rot_gates) * n_qubits * depth

    # Entangling parameters: sum of edges per layer for parametric gates
    ent_params = 0
    if ent_gate.is_parametric:
        edge_counts = count_edges_per_layer(qubits, topo, depth, custom_edges)
        ent_params = sum(edge_counts)

    return rot_params + ent_params


def hea(
    n_qubits: int,
    depth: int = 1,
    qubits: list[int] | None = None,
    params: Union["Parameters", np.ndarray] | None = None,
    *,
    rotation_gates: list[str | RotationGate] | None = None,
    entangling_gate: str | EntanglingGate | None = None,
    topology: str | EntanglementTopology | None = None,
    custom_edges: list[tuple[int, int]] | None = None,
    backend_info: Optional["BackendInfo"] = None,
) -> Circuit:
    """Build a Hardware-Efficient Ansatz (HEA) circuit.

    The ansatz consists of *depth* repeated layers.  Each layer applies:

    1. Single-qubit rotations on every qubit (parameterised).
    2. Entangling gates following the specified topology.

    Args:
        n_qubits: Number of qubits.
        depth: Number of repeated layers (default 1).
        qubits: Qubit indices.  ``None`` → ``list(range(n_qubits))``.
        params: 1-D array of rotation angles.  ``None`` → random initialisation.
        rotation_gates: List of single-qubit rotation types per qubit per layer.
            Default: ``[RotationGate.RZ, RotationGate.RY]`` (backward-compatible).
            Options: ``[RotationGate.RX]``, ``[RotationGate.RX, RotationGate.RY, RotationGate.RZ]``, etc.
        entangling_gate: Two-qubit entangling gate type.
            Default: ``EntanglingGate.CNOT`` (backward-compatible).
            Options: ``EntanglingGate.CZ``, ``EntanglingGate.CRX``, ``EntanglingGate.XX``, etc.
            Parametric gates (CRX, CRY, CRZ, XX, YY, ZZ) consume 1 extra param per edge.
        topology: Entanglement topology for the entangling layer.
            Default: ``EntanglementTopology.RING`` (backward-compatible).
            Options:
            - ``LINEAR``: Chain (0-1, 1-2, 2-3, ...)
            - ``RING``: Linear plus wrap-around (0-1, 1-2, ..., n-1, n-1-0)
            - ``FULL``: All-to-all pairwise
            - ``STAR``: One central qubit to all others
            - ``BRICKWORK``: Alternating even/odd pairs (Qiskit-style)
            - ``CUSTOM``: Use custom_edges parameter
        custom_edges: Required when topology is CUSTOM.
            List of (control, target) qubit pairs.
        backend_info: Backend information for automatic topology/gate selection.
            When provided, automatically selects topology and entangling gate
            that match the hardware capabilities.

    Returns:
        A :class:`Circuit` object containing the ansatz gates.

    Raises:
        ValueError: Parameter count mismatch or invalid configuration.

    Example:
        >>> from uniqc.algorithms.core.ansatz import hea
        >>> c = hea(n_qubits=4, depth=2)
        >>> c.max_qubit + 1
        4

        Custom rotation gates (Rx + Rz):
        >>> c = hea(n_qubits=4, rotation_gates=["rx", "rz"])

        CZ entangling gate with linear topology:
        >>> c = hea(n_qubits=4, entangling_gate="cz", topology="linear")

        Hardware-aware (auto-select topology and gate):
        >>> from uniqc import get_backend
        >>> backend = get_backend("originq:Simulator")
        >>> c = hea(n_qubits=4, backend_info=backend)
    """
    qubits = list(range(n_qubits)) if qubits is None else list(qubits)

    # Handle auto-config from backend_info
    if backend_info is not None:
        topo, gate, edges = select_ansatz_config(backend_info, n_qubits)
        if topology is None:
            topology = topo
        if entangling_gate is None:
            entangling_gate = gate
        if custom_edges is None:
            custom_edges = edges

    # Normalize all inputs
    rot_gates = _normalize_rotation_gates(rotation_gates)
    ent_gate = _normalize_entangling_gate(entangling_gate)
    topo = _normalize_topology(topology)

    # Calculate required parameter count
    rot_params_per_layer = len(rot_gates) * n_qubits

    edge_counts: list[int] = []
    if ent_gate.is_parametric:
        edge_counts = count_edges_per_layer(qubits, topo, depth, custom_edges)
        ent_params_per_layer = edge_counts
    else:
        ent_params_per_layer = [0] * depth

    n_params = rot_params_per_layer * depth + sum(ent_params_per_layer)

    # Import Parameters for auto-generation
    from uniqc.circuit_builder.parameter import Parameters as ParamClass

    # Initialize params - accept both Parameters and np.ndarray
    if params is None:
        # Auto-generate named Parameters
        params = ParamClass("theta_hea", size=n_params)
        # Initialize with random values for immediate use
        rng = np.random.default_rng(0)
        param_values = rng.uniform(0, 2 * np.pi, size=n_params)
        params.bind(list(param_values))
    elif isinstance(params, ParamClass):
        # Validate size
        if len(params) != n_params:
            raise ValueError(
                format_enriched_message(
                    f"Expected {n_params} parameters, got {len(params)}. "
                    f"rot_params={rot_params_per_layer * depth}, ent_params={sum(ent_params_per_layer)}",
                    "circuit_validation",
                )
            )
        # Ensure Parameters are bound for gate evaluation
        if not params[0].is_bound:
            rng = np.random.default_rng(0)
            param_values = rng.uniform(0, 2 * np.pi, size=n_params)
            params.bind(list(param_values))
    else:
        # Convert np.ndarray to list for Parameters
        params_arr = np.asarray(params)
        if len(params_arr) != n_params:
            raise ValueError(
                format_enriched_message(
                    f"Expected {n_params} parameters, got {len(params_arr)}. "
                    f"rot_params={rot_params_per_layer * depth}, ent_params={sum(ent_params_per_layer)}",
                    "circuit_validation",
                )
            )
        params = ParamClass("theta_hea", size=n_params)
        params.bind(list(params_arr.flatten()))

    circuit = Circuit()
    idx = 0

    # Build the circuit
    for layer in range(depth):
        # Single-qubit rotations
        for q in qubits:
            for gate in rot_gates:
                val = params[idx].evaluate()
                if abs(val) > 1e-15:
                    _apply_rotation(circuit, q, gate, val)
                idx += 1

        # Entangling layer
        edges = generate_edges(qubits, topo, custom_edges, layer)
        ent_func = _ENTANGLING_DISPATCH[ent_gate]

        for u, v in edges:
            if ent_gate.is_parametric:
                theta = params[idx].evaluate() if idx < len(params) else 0.0
                idx += 1
            else:
                theta = 0.0
            if ent_gate in (EntanglingGate.XX, EntanglingGate.YY, EntanglingGate.ZZ):
                # These gates need angle * 2
                ent_func(circuit, u, v, theta * 2)
            else:
                ent_func(circuit, u, v, theta)

    # Attach parameters to circuit for traceability
    circuit._params = params

    return circuit


def _apply_rotation(circuit: Circuit, qubit: int, gate: RotationGate, angle: float) -> None:
    """Apply a single-qubit rotation gate."""
    if gate == RotationGate.RX:
        circuit.rx(qubit, angle)
    elif gate == RotationGate.RY:
        circuit.ry(qubit, angle)
    elif gate == RotationGate.RZ:
        circuit.rz(qubit, angle)
    else:
        raise ValueError(f"Unknown rotation gate: {gate}")
