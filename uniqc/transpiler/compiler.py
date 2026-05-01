"""Enhanced transpiler with chip-characterization-aware routing.

This module provides the canonical :func:`compile` entry point for chip-aware
circuit transpilation in UnifiedQuantum. It wraps the existing Qiskit-based
transpiler and adds fidelity-weighted routing, multiple output formats, and a
typed configuration object.
"""

from __future__ import annotations

__all__ = ["compile", "TranspilerConfig", "CompilationResult", "CompilationFailedException"]

import heapq
import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from ._utils import CompilationFailedException
from .converter import convert_oir_to_qasm, convert_qasm_to_oir

if TYPE_CHECKING:
    from uniqc.backend_info import BackendInfo
    from uniqc.circuit_builder import Circuit
    from uniqc.cli.chip_info import ChipCharacterization

OutputFormat = Literal["circuit", "originir", "qasm"]

# Default basis gates for superconducting qubit platforms
_DEFAULT_BASIS_GATES = ("cz", "sx", "rz")

# Default fidelity assumed for edges/qubits not in characterization
_DEFAULT_FIDELITY = 0.99


@dataclass(frozen=True)
class TranspilerConfig:
    """Configuration for the :func:`compile` function.

    Parameters
    ----------
    type : str
        Transpiler backend. Currently only ``"qiskit"`` is supported.
        The string is kept for future extensibility.
    level : int
        Qiskit optimization level (0–3). Default: 2.
        0 = no optimization, 1 = light, 2 = heavy, 3 = heaviest.
    basis_gates : tuple[str, ...]
        Target basis gate set. Default: ``("cz", "sx", "rz")``.
    chip_characterization : ChipCharacterization | None
        Per-qubit and per-pair calibration data. When provided, the router
        prefers higher-fidelity qubits and edges during SWAP insertion and
        qubit routing. If ``None``, routing uses only the connectivity graph.
    """

    type: str = "qiskit"
    level: int = 2
    basis_gates: tuple[str, ...] = _DEFAULT_BASIS_GATES
    chip_characterization: ChipCharacterization | None = None

    def __post_init__(self) -> None:
        if self.type not in ("qiskit",):
            raise ValueError(f"Unsupported transpiler type: {self.type!r}. Only 'qiskit' is supported.")
        if not 0 <= self.level <= 3:
            raise ValueError(f"optimization_level must be 0–3, got {self.level}")
        object.__setattr__(self, "basis_gates", tuple(self.basis_gates or _DEFAULT_BASIS_GATES))


@dataclass
class CompilationResult:
    """Result of a :func:`compile` call.

    Attributes
    ----------
    output : Circuit | str
        Compiled circuit. Type depends on ``output_format`` passed to :func:`compile`.
    fidelity_estimate : float | None
        Estimated success probability of the compiled circuit on the target chip,
        computed from per-gate fidelities in the chip characterization.
        ``None`` if no chip_characterization was provided.
    routing_overhead : int
        Number of SWAP gates inserted by the router.
        Zero if the circuit already fits the topology.
    transpiler_messages : list[str]
        Informational messages from the transpiler.
    """

    output: Circuit | str
    fidelity_estimate: float | None
    routing_overhead: int
    transpiler_messages: list[str] = field(default_factory=list)


def compile(
    circuit: Circuit | str,
    backend_info: BackendInfo | None = None,
    *,
    type: str = "qiskit",
    level: int = 2,
    basis_gates: list[str] | None = None,
    chip_characterization: ChipCharacterization | None = None,
    output_format: OutputFormat = "circuit",
) -> Circuit | str:
    """Compile a circuit for a specific backend using chip characterization data.

    This is the canonical entry point for chip-aware transpilation in UnifiedQuantum.
    It supersedes :func:`transpile_originir <uniqc.transpiler.qiskit_transpiler.transpile_originir>`
    by adding chip-characterization-aware routing, a typed configuration object,
    and a Circuit return type.

    Parameters
    ----------
    circuit :
        The input circuit. Accepts a ``Circuit`` object or an OriginIR string.
    backend_info :
        Target backend descriptor. Supplies the topology coupling map.
        If omitted, the topology is taken from ``chip_characterization``.
    type :
        Transpiler backend. Currently only ``"qiskit"`` is supported.
    level :
        Qiskit optimization level (0–3). Default: 2.
    basis_gates :
        Target basis gate set. Default: ``["cz", "sx", "rz"]``.
    chip_characterization :
        Per-qubit and per-pair calibration data. When provided, the router
        prefers high-fidelity qubits and edges during SWAP insertion.
        If ``None``, routing uses only the connectivity graph.
    output_format :
        Return format. ``"circuit"`` (default) returns a new ``Circuit`` object;
        ``"originir"`` returns an OriginIR string;
        ``"qasm"`` returns a QASM2 string.

    Returns
    -------
    Circuit | str
        The compiled circuit in the requested format.

    Raises
    ------
    CompilationFailedException
        If transpilation fails.
    ValueError
        If the transpiler type is unsupported, the optimization level is out
        of range, or no topology information is available.

    Example
    -------
    >>> from uniqc.circuit_builder import Circuit
    >>> from uniqc.transpiler import compile
    >>> circuit = Circuit()
    >>> circuit.h(0); circuit.cnot(0, 1)
    >>> compiled = compile(circuit, level=2)
    >>> print(type(compiled).__name__)
    Circuit
    """
    config = TranspilerConfig(
        type=type,
        level=level,
        basis_gates=tuple(basis_gates) if basis_gates else _DEFAULT_BASIS_GATES,
        chip_characterization=chip_characterization,
    )
    return compile_with_config(circuit, backend_info, config, output_format)


def compile_with_config(
    circuit: Circuit | str,
    backend_info: BackendInfo | None,
    config: TranspilerConfig,
    output_format: OutputFormat,
) -> Circuit | str:
    """Internal compile implementation that accepts a :class:`TranspilerConfig`."""
    messages: list[str] = []

    # Resolve topology
    if backend_info is not None and backend_info.topology:
        topology = [(e.u, e.v) for e in backend_info.topology]
    elif config.chip_characterization is not None and config.chip_characterization.connectivity:
        topology = [(e.u, e.v) for e in config.chip_characterization.connectivity]
    else:
        raise ValueError(
            "compile() requires either backend_info.topology or "
            "chip_characterization.connectivity to determine the coupling map."
        )

    # Resolve input string
    originir_input = circuit.originir if hasattr(circuit, "originir") else str(circuit)

    # Fidelity-weighted routing
    routed_originir = originir_input
    routing_overhead = 0
    fidelity_estimate: float | None = None

    if config.chip_characterization is not None:
        (
            routed_originir,
            routing_overhead,
            fidelity_estimate,
        ) = _route_with_fidelity(routed_originir, topology, config.chip_characterization)
        messages.append(
            f"Routing used chip characterization (SWAP overhead: {routing_overhead}, "
            f"fidelity estimate: {fidelity_estimate:.4f})"
        )
    else:
        messages.append("No chip characterization provided; routing uses topology only.")

    # Convert to QASM for Qiskit
    qasm_input = convert_oir_to_qasm(routed_originir)

    # Qiskit transpilation
    transpile_qasm = _load_transpile_qasm()
    transpiled_qasm = transpile_qasm(
        [qasm_input],
        topology=topology,
        optimization_level=config.level,
        basis_gates=list(config.basis_gates),
    )[0]

    # Build return value
    if output_format == "originir":
        return convert_qasm_to_oir(transpiled_qasm)
    if output_format == "qasm":
        return transpiled_qasm

    output_originir = convert_qasm_to_oir(transpiled_qasm)
    return _originir_to_circuit(output_originir)


def compile_full(
    circuit: Circuit | str,
    backend_info: BackendInfo | None = None,
    *,
    type: str = "qiskit",
    level: int = 2,
    basis_gates: list[str] | None = None,
    chip_characterization: ChipCharacterization | None = None,
    output_format: OutputFormat = "circuit",
) -> CompilationResult:
    """Full compile returning a :class:`CompilationResult` with metadata.

    Equivalent to :func:`compile` but also returns routing overhead,
    fidelity estimate, and informational messages.

    Parameters
    ----------
    circuit :
        The input circuit.
    backend_info :
        Target backend descriptor.
    type, level, basis_gates, chip_characterization, output_format :
        Same as :func:`compile`.

    Returns
    -------
    CompilationResult
        The compiled output plus metadata.
    """
    config = TranspilerConfig(
        type=type,
        level=level,
        basis_gates=tuple(basis_gates) if basis_gates else _DEFAULT_BASIS_GATES,
        chip_characterization=chip_characterization,
    )
    messages: list[str] = []

    # Resolve topology
    if backend_info is not None and backend_info.topology:
        topology = [(e.u, e.v) for e in backend_info.topology]
    elif config.chip_characterization is not None and config.chip_characterization.connectivity:
        topology = [(e.u, e.v) for e in config.chip_characterization.connectivity]
    else:
        raise ValueError("compile_full() requires either backend_info.topology or chip_characterization.connectivity.")

    originir_input = circuit.originir if hasattr(circuit, "originir") else str(circuit)
    routed_originir = originir_input
    routing_overhead = 0
    fidelity_estimate: float | None = None

    if config.chip_characterization is not None:
        (
            routed_originir,
            routing_overhead,
            fidelity_estimate,
        ) = _route_with_fidelity(routed_originir, topology, config.chip_characterization)
        messages.append(
            f"Routing used chip characterization (SWAP overhead: {routing_overhead}, "
            f"fidelity estimate: {fidelity_estimate:.4f})"
        )
    else:
        messages.append("No chip characterization; routing uses topology only.")

    qasm_input = convert_oir_to_qasm(routed_originir)
    transpile_qasm = _load_transpile_qasm()
    transpiled_qasm = transpile_qasm(
        [qasm_input],
        topology=topology,
        optimization_level=config.level,
        basis_gates=list(config.basis_gates),
    )[0]

    if output_format == "originir":
        output = convert_qasm_to_oir(transpiled_qasm)
    elif output_format == "qasm":
        output = transpiled_qasm
    else:
        output = _originir_to_circuit(convert_qasm_to_oir(transpiled_qasm))

    return CompilationResult(
        output=output,
        fidelity_estimate=fidelity_estimate,
        routing_overhead=routing_overhead,
        transpiler_messages=messages,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_transpile_qasm():
    try:
        from .qiskit_transpiler import transpile_qasm
    except ImportError as exc:
        raise CompilationFailedException(
            "compile() requires the optional qiskit dependencies. "
            "Install unified-quantum[qiskit] or run with `uv run --extra qiskit ...`."
        ) from exc
    return transpile_qasm


def _route_with_fidelity(
    originir: str,
    topology: list[tuple[int, int]],
    chip: ChipCharacterization,
) -> tuple[str, int, float]:
    """Chip-aware routing: insert SWAPs preferring high-fidelity edges.

    Uses Dijkstra's algorithm on a weighted graph where edge weight = 1 - fidelity,
    so the shortest (lowest-weight) path corresponds to the highest-fidelity path.
    """
    # Build best 2Q fidelity map per undirected edge
    tq_fid: dict[tuple[int, int], float] = {}
    for tq_data in chip.two_qubit_data:
        for gate in tq_data.gates:
            if gate.fidelity is not None:
                edge = tuple(sorted((tq_data.qubit_u, tq_data.qubit_v)))
                existing = tq_fid.get(edge)
                if existing is None or gate.fidelity > existing:
                    tq_fid[edge] = gate.fidelity

    # Build weighted adjacency list
    adj: dict[int, list[tuple[int, float]]] = defaultdict(list)
    seen: set[tuple[int, int]] = set()
    for u, v in topology:
        edge = tuple(sorted((u, v)))
        if edge in seen:
            continue
        seen.add(edge)
        fid = tq_fid.get(edge, _DEFAULT_FIDELITY)
        weight = 1.0 - fid
        adj[u].append((v, weight))
        adj[v].append((u, weight))

    # Parse OriginIR
    lines = originir.strip().splitlines()
    routed_lines: list[str] = []
    swap_count = 0

    # Build fidelity maps for estimate
    sq_fid: dict[int, float] = {}
    for sq_data in chip.single_qubit_data:
        if sq_data.single_gate_fidelity is not None:
            sq_fid[sq_data.qubit_id] = sq_data.single_gate_fidelity

    # Determine number of qubits from QINIT line
    n_qubits = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("QINIT"):
            n_qubits = int(stripped.split()[1])
            break
    logical_to_physical = {i: i for i in range(n_qubits)}
    physical_to_logical = {i: i for i in range(n_qubits)}

    from uniqc.originir.originir_line_parser import OriginIR_LineParser

    for line in lines:
        stripped = line.strip()
        # Pass through metadata / non-gate lines
        if not stripped or stripped.startswith(("QINIT", "CREG", "MEASURE", "BARRIER")):
            routed_lines.append(line)
            continue

        try:
            op, qubit, cbit, param, dagger, ctrl = OriginIR_LineParser.parse_line(stripped)
        except Exception:
            routed_lines.append(line)
            continue

        if op is None:
            routed_lines.append(line)
            continue

        # Single-qubit gate: pass through
        if isinstance(qubit, int):
            routed_lines.append(line)
            continue

        # Multi-qubit gate
        if isinstance(qubit, list) and len(qubit) >= 2:
            q0, q1 = qubit[0], qubit[1]
            p0 = logical_to_physical.get(q0, q0)
            p1 = logical_to_physical.get(q1, q1)

            # Check adjacency
            neighbors = {v for v, _ in adj.get(p0, [])}
            if p1 not in neighbors:
                # Need SWAPs: find path p0 -> ... -> p1
                path = _dijkstra_path(p0, p1, adj)
                if path is None:
                    path = _bfs_path(p0, p1, adj)

                if path and len(path) > 1:
                    for i in range(len(path) - 1):
                        a, b = path[i], path[i + 1]
                        routed_lines.append(f"SWAP q[{a}], q[{b}]")
                        swap_count += 1
                        l_a = physical_to_logical[a]
                        l_b = physical_to_logical[b]
                        physical_to_logical[a], physical_to_logical[b] = l_b, l_a
                        logical_to_physical[l_a] = b
                        logical_to_physical[l_b] = a

            routed_lines.append(line)
            continue

        routed_lines.append(line)

    fidelity = _estimate_circuit_fidelity_from_lines(
        routed_lines, sq_fid, tq_fid, logical_to_physical, physical_to_logical
    )

    return "\n".join(routed_lines), swap_count, fidelity


def _dijkstra_path(start: int, end: int, adj: dict[int, list[tuple[int, float]]]) -> list[int] | None:
    """Find minimum-weight path from start to end using Dijkstra."""
    dist: dict[int, float] = {start: 0.0}
    prev: dict[int, int] = {}
    pq: list[tuple[float, int]] = [(0.0, start)]

    while pq:
        d, u = heapq.heappop(pq)
        if u == end:
            path = []
            cur = end
            while cur in prev:
                path.append(cur)
                cur = prev[cur]
            path.append(start)
            path.reverse()
            return path
        if d > dist.get(u, float("inf")):
            continue
        for v, w in adj.get(u, []):
            nd = d + w
            if nd < dist.get(v, float("inf")):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    return None


def _bfs_path(start: int, end: int, adj: dict[int, list[tuple[int, float]]]) -> list[int] | None:
    """Unweighted BFS fallback path finder."""
    queue: deque[tuple[int, list[int]]] = deque([(start, [start])])
    visited = {start}
    while queue:
        node, path = queue.popleft()
        if node == end:
            return path
        for neighbor, _ in adj.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))
    return None


def _estimate_circuit_fidelity_from_lines(
    lines: list[str],
    sq_fid: dict[int, float],
    tq_fid: dict[tuple[int, int], float],
    l2p: dict[int, int],
    p2l: dict[int, int],
) -> float:
    """Compute product-of-fidelities estimate from OriginIR lines."""
    from uniqc.originir.originir_line_parser import OriginIR_LineParser

    fidelity = 1.0
    measured_qubits: set[int] = set()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("MEASURE"):
            measured_qubits.update(int(q) for q in re.findall(r"q\[(\d+)\]", stripped))
            continue

        try:
            op, qubit, *_ = OriginIR_LineParser.parse_line(stripped)
        except Exception:
            continue

        if op is None or op in (
            "QINIT",
            "CREG",
            "CONTROL",
            "ENDCONTROL",
            "DAGGER",
            "ENDDAGGER",
            "BARRIER",
            "SWAP",
            "DEF",
            "ENDDEF",
        ):
            continue

        if isinstance(qubit, int):
            p = l2p.get(qubit, qubit)
            fidelity *= sq_fid.get(p, _DEFAULT_FIDELITY)
        elif isinstance(qubit, list) and len(qubit) >= 2:
            p0 = l2p.get(qubit[0], qubit[0])
            p1 = l2p.get(qubit[1], qubit[1])
            edge = tuple(sorted((p0, p1)))
            fidelity *= tq_fid.get(edge, _DEFAULT_FIDELITY)

    return max(0.0, min(1.0, fidelity))


def _originir_to_circuit(originir_str: str) -> Circuit:
    """Parse an OriginIR string into a Circuit object."""
    from uniqc.circuit_builder import Circuit
    from uniqc.originir.originir_line_parser import OriginIR_LineParser

    circuit: Circuit = Circuit()
    lines = originir_str.strip().splitlines()
    pending_measurements: dict[int, int] = {}

    GATE_MAP: dict[str, str] = {
        "H": "h",
        "X": "x",
        "Y": "y",
        "Z": "z",
        "S": "s",
        "T": "t",
        "SX": "sx",
        "I": "i",
        "CNOT": "cnot",
        "CZ": "cz",
        "SWAP": "swap",
        "ISWAP": "iswap",
        "TOFFOLI": "toffoli",
        "CSWAP": "cswap",
        "ECR": "ecr",
    }

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        try:
            op, qubit, cbit, param, dagger, ctrl = OriginIR_LineParser.parse_line(stripped)
        except Exception:
            # Try to handle SWAP, QINIT, CREG, MEASURE naively
            if stripped.startswith("SWAP"):
                m = re.findall(r"q\[(\d+)\]", stripped)
                if len(m) == 2:
                    circuit.swap(int(m[0]), int(m[1]))
                continue
            if stripped.startswith("QINIT"):
                n = int(stripped.split()[1])
                # Set circuit size; Circuit will populate itself from opcodes
                circuit.qubit_num = n
                circuit.max_qubit = max(0, n - 1)
                continue
            if stripped.startswith("CREG"):
                circuit.cbit_num = int(stripped.split()[1])
                continue
            if "MEASURE" in stripped:
                q_match = re.search(r"q\[(\d+)\]", stripped)
                c_match = re.search(r"c\[(\d+)\]", stripped)
                if q_match is not None and c_match is not None:
                    pending_measurements[int(c_match.group(1))] = int(q_match.group(1))
                continue
            # Skip unparseable lines
            continue

        if op == "QINIT":
            circuit.qubit_num = int(qubit)
            circuit.max_qubit = max(0, circuit.qubit_num - 1)
            continue
        if op == "CREG":
            circuit.cbit_num = int(cbit or 0)
            continue
        if op is None or op in ("CONTROL", "ENDCONTROL", "DAGGER", "ENDDAGGER", "DEF", "ENDDEF"):
            continue
        if op == "MEASURE":
            pending_measurements[int(cbit)] = int(qubit)
            circuit.record_qubit(int(qubit))
            continue
        if op == "BARRIER":
            q_ids = [int(q) for q in re.findall(r"q\[(\d+)\]", stripped)]
            if q_ids:
                circuit.barrier(*q_ids)
            continue

        # Map gate name to Circuit method
        method_name = GATE_MAP.get(op, op.lower())
        if hasattr(circuit, method_name):
            fn = getattr(circuit, method_name)
            try:
                if isinstance(qubit, list):
                    args = qubit[:]
                    if param is not None:
                        if isinstance(param, (list, tuple)):
                            args.extend(param)
                        else:
                            args.append(param)
                    fn(*args)
                elif isinstance(qubit, int):
                    if param is not None:
                        if isinstance(param, (list, tuple)):
                            fn(qubit, *param)
                        else:
                            fn(qubit, param)
                    else:
                        fn(qubit)
            except TypeError:
                circuit.add_gate(op, qubit, cbit, param, bool(dagger), ctrl)
        else:
            circuit.add_gate(op, qubit, cbit, param, bool(dagger), ctrl)

    if pending_measurements:
        circuit.measure_list = [pending_measurements[cbit] for cbit in sorted(pending_measurements)]
        circuit.cbit_num = max(pending_measurements) + 1
        circuit.record_qubit(circuit.measure_list)

    return circuit
