"""Per-platform submission policy: basis gates, language, compile dispatch.

This module is the single source of truth for "what does each cloud platform
expect from a circuit before we hand it over". Two pieces of policy live here:

* :data:`PLATFORM_BASIS_GATES` — the gate set we compile to before submission
  on each platform. For superconducting CN-style platforms (originq, quafu,
  quark) we use ``("CZ", "SX", "RZ")``. For IBM we defer to the backend's
  advertised ``basis_gates`` (read from
  :attr:`BackendInfo.extra` ``["basis_gates"]``) and fall back to qiskit's
  defaults if missing.

* :data:`PLATFORM_SUBMIT_LANGUAGE` — the IR string each adapter actually sends
  on the wire. ``OriginIR`` for OriginQ (pyqpanda3 path) and ``QASM2`` for
  qiskit / quafu / quark.

The high-level helper :func:`compile_for_backend` glues the policy and the
existing :func:`uniqc.compile.compile` function together, returning a circuit
that is ready to submit (gate set + language) for the given backend.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uniqc.backend_adapter.backend_info import BackendInfo
    from uniqc.circuit_builder.qcircuit import Circuit

__all__ = [
    "PLATFORM_BASIS_GATES",
    "PLATFORM_SUBMIT_LANGUAGE",
    "resolve_basis_gates",
    "resolve_submit_language",
    "compile_for_backend",
]


#: Default basis gate set per platform (uppercase, OriginIR/qiskit names).
#: Empty tuple means "no opinion — defer to the backend's own advertisement".
PLATFORM_BASIS_GATES: dict[str, tuple[str, ...]] = {
    "originq": ("CZ", "SX", "RZ"),
    "quafu": ("CZ", "SX", "RZ"),
    "quark": ("CZ", "SX", "RZ"),
    "ibm": (),  # IBM: take from backend.extra["basis_gates"]
    "dummy": (),
}


#: The wire language each adapter submits with.
PLATFORM_SUBMIT_LANGUAGE: dict[str, str] = {
    "originq": "OriginIR",
    "quafu": "QASM2",
    "quark": "QASM2",
    "ibm": "QASM2",
    "dummy": "OriginIR",
}


def _platform_key(backend: str | BackendInfo) -> str:
    if hasattr(backend, "platform"):
        return backend.platform.value  # type: ignore[union-attr]
    s = str(backend)
    return s.split(":", 1)[0].lower()


def resolve_submit_language(backend: str | BackendInfo) -> str | None:
    """Return the wire language for ``backend`` or ``None`` if unknown."""
    return PLATFORM_SUBMIT_LANGUAGE.get(_platform_key(backend))


def resolve_basis_gates(
    backend: str | BackendInfo,
    backend_info: BackendInfo | None = None,
) -> tuple[str, ...]:
    """Return the basis gate set we will compile to before submission.

    Resolution order:
        1. Platform default from :data:`PLATFORM_BASIS_GATES` if non-empty.
        2. ``backend_info.extra["basis_gates"]`` if non-empty.
        3. Empty tuple — caller should treat this as "skip compile".
    """
    key = _platform_key(backend)
    default = PLATFORM_BASIS_GATES.get(key, ())
    if default:
        return default
    info = backend_info if backend_info is not None else (backend if hasattr(backend, "extra") else None)
    if info is not None and info.extra:
        raw = info.extra.get("basis_gates") or ()
        return tuple(str(g).upper() for g in raw)
    return ()


def compile_for_backend(
    circuit: Circuit,
    backend_info: BackendInfo,
    *,
    level: int = 2,
    output_format: str = "circuit",
):
    """Compile ``circuit`` so that it satisfies ``backend_info``.

    For ``originq``, ``quafu`` and ``quark`` this lowers the circuit to
    ``cz + sx + rz`` (the supported superconducting basis) using the existing
    :func:`uniqc.compile.compile` pipeline. For ``ibm``, the basis set is
    read from the backend's advertised ``basis_gates`` (typically
    ``("CZ", "SX", "RZ", "X")`` plus IBM-specific extras). When the backend
    does not advertise a basis set, qiskit's default is used.

    Parameters
    ----------
    circuit :
        Source UnifiedQuantum :class:`Circuit`.
    backend_info :
        Target backend descriptor. Topology and ``num_qubits`` are used by
        the routing pass.
    level :
        Optimization level (0–3) for the underlying transpiler. Default: 2.
    output_format :
        ``"circuit"`` (default) returns a :class:`Circuit`;
        ``"originir"`` returns an OriginIR string;
        ``"qasm"`` returns an OpenQASM 2.0 string.

    Returns
    -------
    Circuit | str
        The compiled circuit in the requested format.
    """
    from uniqc.compile.compiler import compile as _compile

    basis = list(resolve_basis_gates(backend_info, backend_info))
    if not basis:
        # Last-ditch superconducting default; matches qiskit & uniqc default.
        basis = ["cz", "sx", "rz"]
    # uniqc.compile.compile expects lowercase basis gate names.
    basis = [g.lower() for g in basis]

    return _compile(
        circuit,
        backend_info=backend_info,
        level=level,
        basis_gates=basis,
        output_format=output_format,
    )
