### WK180 chip-wide parallel-CZ XEB example for UnifiedQuantum.

*Source*: ``examples/2_advanced/wk180/xeb.py``  
*Status*: **not-executed**

This example partitions every CZ edge of OriginQ's WK_C180 chip into
three disjoint matchings (3-edge-coloring), picks one matching, and
runs a chip-wide *parallel* 2-qubit XEB on that single matching. The
full N-qubit circuit factorises as a tensor product over the disjoint
pairs of the matching, so per-pair F_XEB(d) decays — and therefore
per-pair CZ fidelities — fall out of 2-qubit marginals of the
chip-wide bitstring (no 2^N statevector blow-up needed for analysis).

This is the recommended *pre-flight* characterization step before any
larger experiment that depends on accurate per-pair CZ numbers.

Pre-flight policy (no fallbacks)
--------------------------------
This example refuses to run unless every prerequisite is satisfied:

* ``pyqpanda3`` must be importable (the OriginQ SDK).
* The WK180 chip characterization must be present in the local cache
  *and* younger than 24 hours; otherwise it is refreshed via the
  OriginQ SDK. If the SDK refresh fails (no API key / network /
  invalid chip name), the example aborts with a precise error.
* ``--dummy`` mode is **not** exempt from any of the above — chip-noisy
  simulation is meaningless without real chip data.
* Real-chip submission additionally requires ``--confirm-chip``.

Usage:

    # Inspect the 3-coloring without running anything (still pre-flighted):
    python examples/wk180/xeb.py --list-colors

    # Dummy mode (use --max-qubits to keep the noisy density-op simulator happy):
    python examples/wk180/xeb.py --dummy --max-qubits 10 --color 0

    # Real chip:
    python examples/wk180/xeb.py --backend originq:wuyuan:wk180 \\
        --color 0 --confirm-chip --shots 5000 --instances 20

    # 1q-XEB sanity check on a few qubits:
    python examples/wk180/xeb.py --dummy --type 1q --qubits 0 1 2

**Source code**

```{literalinclude} ../../../examples/2_advanced/wk180/xeb.py
:language: python
```

:::{note}
Listed for reference; not executed during the docs build (``[doc-skip-execute]``).
:::

