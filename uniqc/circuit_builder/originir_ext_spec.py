"""OriginIR-ext language specification — the superset of official OriginIR.

OriginIR-ext extends the official OriginIR (accepted by OriginQ cloud) with:

- **Extended gates**: ECR, ISWAP, XX, YY, ZZ, XY, PHASE2Q, UU15, RPhi, RPhi90,
  RPhi180  (all decomposable to official gates for cloud submission)
- **Extended features**: DEF/ENDDEF blocks, QRAM (Quantum RAM) instructions,
  error channels for noise simulation
- **Symbolic parameters** (local-only): a ``PARAM`` header declaration plus
  inline symbolic parameter references / expressions in gate angle slots — see
  the "Symbolic-parameter extension" note below.
- **Extended syntax**: inline ``dagger`` suffix, inline ``controlled_by(q[...])``
  clause (as an alternative to DAGGER/CONTROL blocks)
- **Classical / control-flow extension** (local-simulation only — see
  :class:`uniqc.simulator.OriginIR_ext_Simulator`):

  * a runtime classical-register (CREG) of single bits ``c[0..n-1]`` (declared
    by ``CREG n``), written by measurement and classical instructions and read
    by conditions;
  * ``MEASURE q[i], c[j]`` as a mid-circuit measurement writing CREG bit ``j``
    (valid both mid-circuit and terminally);
  * ``RESET q[i]`` mid-circuit qubit reset;
  * classical bit instructions ``AND``/``OR``/``XOR`` (``op c[d], A, B``) and
    ``MOV``/``NOT`` (``op c[d], A``), RISC three-operand / destination-first,
    where ``A``/``B`` are CREG bits ``c[k]`` or ``0``/``1`` immediates;
  * classical control flow ``QIF <cond> ... [QELSE ...] ENDQIF`` and
    ``QWHILE <cond> ... ENDQWHILE``, where ``<cond>`` is boolean logic over CREG
    bits using ``not``/``~``, ``and``/``&``, ``xor``/``^``, ``or``/``|`` (lowercase
    keywords and symbols interchangeable) and parentheses.

  These constructs are an OriginIR-ext-only feature and cannot be exported to
  OpenQASM or submitted to cloud backends.

- **Symbolic-parameter extension** (local-only — mirrors the Python
  :class:`~uniqc.circuit_builder.parameter.Parameter` / ``Parameters`` classes):

  * a ``PARAM`` header declaration, either scalar (``PARAM theta``) or array
    (``PARAM alpha[4]``, expanding to the element symbols ``alpha_0..alpha_3``),
    placed after the ``QINIT``/``CREG`` header;
  * inline symbolic parameter references and arithmetic expressions in a gate's
    angle slot, e.g. ``RX q[0], (theta)``, ``RY q[1], (alpha[2])`` or
    ``RZ q[0], (2*theta + phi/3)``.  Expressions are parsed/round-tripped via
    sympy and may not contain commas or parentheses (so no nested groups or
    function calls); split such angles into distinct named parameters instead.

  A circuit carrying unbound ``PARAM`` symbols serializes to OriginIR-ext but
  must be bound to concrete values via
  :meth:`uniqc.circuit_builder.Circuit.assign_parameters` before it can be
  simulated, exported to OpenQASM / official OriginIR, or submitted to cloud.

OriginIR-ext is the **default local programming language** in UnifiedQuantum.
When submitting to OriginQ cloud, circuits are automatically converted to
strict official OriginIR via :func:`uniqc.compile.decompose_for_originir`.

See :mod:`uniqc.circuit_builder.originir_spec` for the official (downstream)
gate set, and :mod:`uniqc.circuit_builder.originir_ext_spec` (this module) for
the full superset.
"""

from .originir_spec import (
    OFFICIAL_ORIGINIR_GATES,
    available_originir_error_channels,
    available_originir_error_channels_without_kraus,
    generate_sub_error_channel_originir,
    generate_sub_gateset_originir,
)
from .originir_spec import (
    available_originir_gates as _official_gates,
)

__all__ = [
    "available_originir_ext_gates",
    "EXTENDED_GATES_ONLY",
    "available_originir_error_channels",
    "available_originir_error_channels_without_kraus",
    "generate_sub_error_channel_originir",
    "generate_sub_gateset_originir",
]

# The full superset gate dictionary — every gate the parser and serializer
# understand.  This is identical to the current ``available_originir_gates``
# but makes the naming explicit.
available_originir_ext_gates: dict[str, dict] = dict(_official_gates)

# SWAP is in the official set (and in the QASM mapping) but was not in
# available_originir_gates.  Add it so the ext superset is truly a superset.
available_originir_ext_gates.setdefault("SWAP", {"qubit": 2, "param": 0})

# QRAM (Quantum Random Access Memory) — a variable-qubit extension declared
# via ``QRAMDECL`` and invoked by name.  ``qubit: -1`` indicates the qubit
# count is determined at runtime by the declaration (like BARRIER).
available_originir_ext_gates.setdefault("QRAM", {"qubit": -1, "param": 0})

# Extended gates that go beyond the official OriginIR specification.
# These must be decomposed before submission to OriginQ cloud.
EXTENDED_GATES_ONLY: frozenset[str] = frozenset(
    set(available_originir_ext_gates) - OFFICIAL_ORIGINIR_GATES
)
