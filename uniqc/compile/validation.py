"""Pre-submission circuit validation and depth analysis.

This module provides backend-agnostic helpers used by every uniqc submission
path to make sure a :class:`~uniqc.circuit_builder.qcircuit.Circuit` is actually
runnable on a target backend before any cloud round-trip happens.

Two public entry points
-----------------------

``compute_gate_depth(circuit, *, virtual_z=True)``
    Returns the parallelism-aware physical depth of ``circuit``. Each layer is
    the earliest position at which all qubits used by an operation are free.
    When ``virtual_z=True`` (the default), gates implemented as a frame change
    on superconducting qubits — :data:`VIRTUAL_Z_GATES` — contribute 0 depth.

``compatibility_report(circuit, backend_info, *, basis_gates=None,
language=None)`` and the boolean shortcut ``is_compatible(...)``
    Validate, in this order:

    1. Language acceptance (the platform's submit language can express the gates).
    2. Qubit count fits within ``backend_info.num_qubits``.
    3. Every gate appears in the (effective) basis set / supported set.
    4. Every two-qubit interaction has a corresponding edge in the topology
       (``CZ``, ``ISWAP``, ``SWAP`` are undirected; ``CNOT`` / ``CX`` /
       ``ECR`` are directional unless the backend marks the edge as
       reversible).

The returned :class:`CompatibilityReport` is the same object surfaced by
``submit_task(..., dry_run=True)`` and printed by the CLI.

This module deliberately does **no** platform-specific compilation; for that
see :mod:`uniqc.compile.policy`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uniqc.backend_adapter.backend_info import BackendInfo
    from uniqc.circuit_builder.qcircuit import Circuit

__all__ = [
    "VIRTUAL_Z_GATES",
    "CompatibilityReport",
    "compute_gate_depth",
    "compatibility_report",
    "is_compatible",
]


# ---------------------------------------------------------------------------
# Gate classification
# ---------------------------------------------------------------------------

#: Gates that are typically implemented as virtual phase/frame changes on
#: superconducting hardware and therefore contribute 0 physical depth.
#: Conservative default — only includes gates whose physical implementation is
#: a software phase update on every major superconducting cloud platform.
VIRTUAL_Z_GATES: frozenset[str] = frozenset({"Z", "RZ", "S", "T", "U1"})

#: Gates whose two-qubit interaction is symmetric on hardware
#: (no implicit direction).
_UNDIRECTED_2Q_GATES: frozenset[str] = frozenset({"CZ", "ISWAP", "SWAP", "ZZ", "XX", "YY", "XY"})

#: Common aliases — normalised before comparison against the basis set.
_GATE_ALIASES: dict[str, str] = {
    "CX": "CNOT",
    "ID": "I",
    "P": "U1",
    "PHASE": "U1",
    "TDG": "T",
    "SDG": "S",
    "SXDG": "SX",
}

#: Operations that are not "gates" for the purpose of basis / topology checks.
_NON_GATE_OPS: frozenset[str] = frozenset(
    {
        "QINIT",
        "CREG",
        "MEASURE",
        "BARRIER",
        "CONTROL",
        "ENDCONTROL",
        "DAGGER",
        "ENDDAGGER",
        "DEF",
        "ENDDEF",
        "I",
    }
)


def _normalise_gate_name(name: str) -> str:
    """Upper-case and de-alias a gate name."""
    n = name.upper()
    return _GATE_ALIASES.get(n, n)


# ---------------------------------------------------------------------------
# Report dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompatibilityReport:
    """Result of :func:`compatibility_report`.

    Attributes
    ----------
    compatible :
        ``True`` iff every check passed. ``submit_task()`` refuses to submit
        when this is ``False``.
    backend_id :
        Full backend identifier (``platform:name``) the report was computed for.
    used_qubits :
        Set of qubit indices touched by any gate or measurement.
    used_gates :
        Set of gate names (post-alias-normalisation) used by the circuit.
    gate_depth :
        Parallelism-aware physical depth (with virtual-Z if requested).
    errors :
        Hard failures — caller must not submit.
    warnings :
        Soft issues, e.g. partial validation due to missing topology data.
    """

    compatible: bool
    backend_id: str | None
    used_qubits: frozenset[int]
    used_gates: frozenset[str]
    gate_depth: int
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def __bool__(self) -> bool:  # convenience for `if report:`
        return self.compatible

    def __str__(self) -> str:
        head = "OK" if self.compatible else "FAIL"
        backend = self.backend_id or "<no backend>"
        lines = [
            f"CompatibilityReport({head}) backend={backend}"
            f" qubits={len(self.used_qubits)} depth={self.gate_depth}"
            f" gates={sorted(self.used_gates)}",
        ]
        for e in self.errors:
            lines.append(f"  ERROR: {e}")
        for w in self.warnings:
            lines.append(f"  WARN:  {w}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal: opcode iteration
# ---------------------------------------------------------------------------


def _iter_gate_opcodes(circuit: Circuit):
    """Yield ``(name, qubits, is_measure_or_barrier)`` for every opcode.

    Resolves control qubits embedded in opcodes so that they participate in
    depth and topology checks.
    """
    for op in circuit.opcode_list:
        # OpCode = (op_name, qubits, cbits, params, dagger, control_qubits)
        op_name, qubits, _cbits, _params, _dagger, control_qubits = op
        name = _normalise_gate_name(str(op_name))

        if isinstance(qubits, int):
            qubit_list = [qubits]
        elif isinstance(qubits, (list, tuple)):
            qubit_list = [int(q) for q in qubits]
        else:
            qubit_list = []

        if isinstance(control_qubits, (list, tuple)) and control_qubits:
            qubit_list = [int(c) for c in control_qubits] + qubit_list
        elif isinstance(control_qubits, int):
            qubit_list = [int(control_qubits)] + qubit_list

        is_measure = name == "MEASURE"
        is_barrier = name == "BARRIER"
        yield name, qubit_list, (is_measure or is_barrier)

    # Trailing measurements collected via circuit.measure(...) but not pushed
    # to opcode_list yet.
    for q in getattr(circuit, "measure_list", None) or []:
        yield "MEASURE", [int(q)], True


# ---------------------------------------------------------------------------
# compute_gate_depth
# ---------------------------------------------------------------------------


def compute_gate_depth(circuit: Circuit, *, virtual_z: bool = True) -> int:
    """Return the parallelism-aware physical depth of ``circuit``.

    Parameters
    ----------
    circuit :
        Input UnifiedQuantum :class:`~uniqc.circuit_builder.qcircuit.Circuit`.
    virtual_z :
        When ``True`` (default), gates in :data:`VIRTUAL_Z_GATES` contribute
        zero depth — they are implemented as a frame change on superconducting
        qubits. They still occupy their qubit's "schedule cursor" so that
        non-commuting gates around them are not collapsed into one layer.

    Returns
    -------
    int
        The depth, i.e. the maximum number of non-virtual layers any qubit
        participates in. A circuit with no non-virtual gates has depth 0.

    Notes
    -----
    * ``MEASURE`` and ``BARRIER`` are not counted as gate depth, but
      ``BARRIER`` synchronises every qubit it touches: subsequent gates on
      those qubits start at the maximum cursor among them.
    * Multi-qubit gates use the maximum cursor over their qubits + 1 (or +0
      if virtual).
    * The result is platform-agnostic; it estimates depth on a hardware that
      can implement Z gates virtually.
    """
    qubit_cursor: dict[int, int] = {}

    for name, qubits, is_meta in _iter_gate_opcodes(circuit):
        if not qubits:
            continue
        if name == "MEASURE":
            # Measurements do not add to the gate depth in this convention,
            # but we treat them like a barrier on the measured qubit so that
            # later gates (rare) start after them.
            cursor = max(qubit_cursor.get(q, 0) for q in qubits)
            for q in qubits:
                qubit_cursor[q] = cursor
            continue
        if name == "BARRIER":
            cursor = max(qubit_cursor.get(q, 0) for q in qubits)
            for q in qubits:
                qubit_cursor[q] = cursor
            continue
        if is_meta:
            continue

        cursor = max(qubit_cursor.get(q, 0) for q in qubits)
        contribution = 0 if (virtual_z and name in VIRTUAL_Z_GATES) else 1
        new_cursor = cursor + contribution
        for q in qubits:
            qubit_cursor[q] = new_cursor

    if not qubit_cursor:
        return 0
    return max(qubit_cursor.values())


# ---------------------------------------------------------------------------
# Compatibility check
# ---------------------------------------------------------------------------


def _resolve_basis_gates(
    backend_info: BackendInfo | None,
    basis_gates: list[str] | tuple[str, ...] | None,
) -> tuple[frozenset[str] | None, tuple[str, ...]]:
    """Return (effective basis set, warnings).

    Resolution order:
        1. Explicit ``basis_gates`` argument.
        2. ``backend_info.extra["basis_gates"]`` if non-empty.
        3. ``None`` — the gate-set check is skipped with a warning.
    """
    if basis_gates:
        return frozenset(_normalise_gate_name(g) for g in basis_gates), ()
    if backend_info is not None:
        raw = backend_info.extra.get("basis_gates") if backend_info.extra else None
        if raw:
            return frozenset(_normalise_gate_name(g) for g in raw), ()
        return None, (
            f"Backend {backend_info.full_id()} does not advertise a basis_gates list; "
            "skipping gate-set check.",
        )
    return None, ("No backend_info and no basis_gates supplied; skipping gate-set check.",)


def _build_undirected_topology(backend_info: BackendInfo | None) -> set[tuple[int, int]] | None:
    if backend_info is None or not backend_info.topology:
        return None
    edges: set[tuple[int, int]] = set()
    for e in backend_info.topology:
        edges.add((min(e.u, e.v), max(e.u, e.v)))
    return edges


def _build_directed_topology(backend_info: BackendInfo | None) -> set[tuple[int, int]] | None:
    if backend_info is None or not backend_info.topology:
        return None
    return {(int(e.u), int(e.v)) for e in backend_info.topology}


def _check_language(used_gates: frozenset[str], language: str | None) -> tuple[str, ...]:
    """Return errors if ``used_gates`` cannot be expressed in ``language``.

    ``language`` follows :data:`uniqc.compile.policy.PLATFORM_SUBMIT_LANGUAGE`
    values: ``"OriginIR"`` | ``"QASM2"`` | ``None`` (skip).
    """
    if language is None:
        return ()
    # OriginIR and QASM2 both accept the standard set we emit. Surface only
    # gates we know cannot be lowered to QASM2 directly.
    if language.upper() in {"QASM2", "OPENQASM2", "OPENQASM 2.0"}:
        unsupported_in_qasm2 = used_gates & frozenset({"RPHI", "RPHI90", "RPHI180", "PHASE2Q", "UU15"})
        if unsupported_in_qasm2:
            names = ", ".join(sorted(unsupported_in_qasm2))
            return (
                f"Gates {{{names}}} are not expressible in OpenQASM 2.0; "
                "compile() to a portable basis set first.",
            )
    return ()


def compatibility_report(
    circuit: Circuit,
    backend_info: BackendInfo | None,
    *,
    basis_gates: list[str] | tuple[str, ...] | None = None,
    language: str | None = None,
    virtual_z: bool = True,
) -> CompatibilityReport:
    """Validate ``circuit`` against ``backend_info`` and return a full report.

    Parameters
    ----------
    circuit :
        The circuit to validate.
    backend_info :
        Target backend descriptor. May be ``None`` for purely-local checks
        (gate depth, language); in that case topology and qubit-count checks
        are skipped with warnings.
    basis_gates :
        Optional explicit basis set to check against. Falls back to
        ``backend_info.extra["basis_gates"]`` if not given.
    language :
        Submission language for the target platform — see
        :data:`uniqc.compile.policy.PLATFORM_SUBMIT_LANGUAGE`. Used for
        language-level rejections (e.g. RPhi cannot reach QASM2).
    virtual_z :
        Forwarded to :func:`compute_gate_depth`.

    Returns
    -------
    CompatibilityReport
        See class docstring.
    """
    used_qubits: set[int] = set()
    used_gates: set[str] = set()
    two_qubit_interactions: list[tuple[str, int, int]] = []

    for name, qubits, is_meta in _iter_gate_opcodes(circuit):
        for q in qubits:
            used_qubits.add(int(q))
        if is_meta or name in _NON_GATE_OPS:
            continue
        used_gates.add(name)
        if len(qubits) == 2:
            two_qubit_interactions.append((name, int(qubits[0]), int(qubits[1])))

    used_qubits_fz = frozenset(used_qubits)
    used_gates_fz = frozenset(used_gates)

    errors: list[str] = []
    warnings: list[str] = []

    # 1. Language
    errors.extend(_check_language(used_gates_fz, language))

    # 2. Qubit count
    if backend_info is not None and backend_info.num_qubits:
        max_q = max(used_qubits, default=-1)
        if max_q >= backend_info.num_qubits:
            errors.append(
                f"Circuit uses qubit q[{max_q}] but backend "
                f"{backend_info.full_id()} only has {backend_info.num_qubits} qubits."
            )

    # 3. Gate set
    basis, basis_warnings = _resolve_basis_gates(backend_info, basis_gates)
    warnings.extend(basis_warnings)
    if basis is not None:
        out_of_basis = sorted(g for g in used_gates_fz if g not in basis and g not in _NON_GATE_OPS)
        if out_of_basis:
            errors.append(
                f"Circuit uses gates outside the backend basis set: "
                f"{out_of_basis}. Allowed: {sorted(basis)}."
            )

    # 4. Topology
    undirected = _build_undirected_topology(backend_info)
    directed = _build_directed_topology(backend_info)
    if backend_info is None:
        if two_qubit_interactions:
            warnings.append("No backend_info supplied; skipping topology check.")
    elif undirected is None:
        if two_qubit_interactions:
            warnings.append(
                f"Backend {backend_info.full_id()} reports no topology; skipping topology check."
            )
    else:
        bad: list[str] = []
        for gname, a, b in two_qubit_interactions:
            edge = (min(a, b), max(a, b))
            if edge not in undirected:
                bad.append(f"{gname} q[{a}], q[{b}]")
                continue
            # Directional gates need the exact (a, b) edge unless the backend
            # is symmetric (every edge appears in both directions).
            if gname not in _UNDIRECTED_2Q_GATES and directed is not None:
                if (a, b) not in directed and (b, a) not in directed:
                    bad.append(f"{gname} q[{a}], q[{b}]  (no edge)")
                elif (a, b) not in directed and (b, a) in directed:
                    # Backend lists only the reverse direction; flag as warning
                    # (the compiler can fix this with H sandwich).
                    warnings.append(
                        f"{gname} q[{a}], q[{b}] uses reverse direction of the "
                        "advertised hardware edge — compile() will need to flip it."
                    )
        if bad:
            errors.append(
                "Two-qubit gates violate the backend topology: "
                + "; ".join(bad)
            )

    depth = compute_gate_depth(circuit, virtual_z=virtual_z)

    return CompatibilityReport(
        compatible=not errors,
        backend_id=backend_info.full_id() if backend_info is not None else None,
        used_qubits=used_qubits_fz,
        used_gates=used_gates_fz,
        gate_depth=depth,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def is_compatible(
    circuit: Circuit,
    backend_info: BackendInfo | None,
    *,
    basis_gates: list[str] | tuple[str, ...] | None = None,
    language: str | None = None,
) -> bool:
    """Boolean shortcut around :func:`compatibility_report`.

    Returns ``True`` iff topology, gate set and language all check out.
    For the full report (depth, used gates, warnings, error messages),
    use :func:`compatibility_report`.
    """
    return compatibility_report(
        circuit,
        backend_info,
        basis_gates=basis_gates,
        language=language,
    ).compatible


# ---------------------------------------------------------------------------
# Convenience for callers that have an OriginIR string instead of a Circuit
# ---------------------------------------------------------------------------

_QINIT_RE = re.compile(r"^\s*QINIT\s+(\d+)\s*$", re.MULTILINE)
