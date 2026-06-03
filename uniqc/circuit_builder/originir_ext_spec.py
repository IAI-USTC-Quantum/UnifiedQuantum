"""OriginIR-ext language specification — the superset of official OriginIR.

OriginIR-ext extends the official OriginIR (accepted by OriginQ cloud) with:

- **Extended gates**: ECR, ISWAP, XX, YY, ZZ, XY, PHASE2Q, UU15, RPhi, RPhi90,
  RPhi180  (all decomposable to official gates for cloud submission)
- **Extended features**: DEF/ENDDEF blocks, error channels for noise simulation
- **Extended syntax**: inline ``dagger`` suffix, inline ``controlled_by(q[...])``
  clause (as an alternative to DAGGER/CONTROL blocks)

OriginIR-ext is the **default local programming language** in UnifiedQuantum.
When submitting to OriginQ cloud, circuits are automatically converted to
strict official OriginIR via :func:`uniqc.compile.decompose_for_originir`.

See :mod:`uniqc.circuit_builder.originir_spec` for the official (downstream)
gate set, and :mod:`uniqc.circuit_builder.originir_ext_spec` (this module) for
the full superset.
"""

from .originir_spec import (
    OFFICIAL_ORIGINIR_GATES,
    available_originir_gates as _official_gates,
)
from .originir_spec import (
    available_originir_error_channels,
    available_originir_error_channels_without_kraus,
    generate_sub_error_channel_originir,
    generate_sub_gateset_originir,
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

# Extended gates that go beyond the official OriginIR specification.
# These must be decomposed before submission to OriginQ cloud.
EXTENDED_GATES_ONLY: frozenset[str] = frozenset(
    set(available_originir_ext_gates) - OFFICIAL_ORIGINIR_GATES
)
