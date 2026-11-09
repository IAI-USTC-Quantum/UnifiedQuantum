### WK180 readout EM example for UnifiedQuantum.

*Source*: ``examples/2_advanced/wk180/readout_em.py``  
*Status*: **not-executed**

This example demonstrates calibrating and applying readout error mitigation
on the WK180 quantum processor from OriginQ.

Usage:
    # Dummy mode
    python examples/wk180/readout_em.py --dummy --qubits 0 1 2

    # Real machine
    python examples/wk180/readout_em.py --backend originq:wuyuan:wk180 --qubits 0 1 2

**Source code**

```{literalinclude} ../../../examples/2_advanced/wk180/readout_em.py
:language: python
```

:::{note}
Listed for reference; not executed during the docs build (``[doc-skip-execute]``).
:::

