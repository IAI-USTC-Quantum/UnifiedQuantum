### 02 — Independent local quantum lab

*Source*: ``examples/5_webui/02_local_quantum_lab.py``  
*Status*: **pass**

The CLI and browser use these same local presets and the existing native
simulation path. Only exact probabilities and analytic errors are printed;
wall time is deliberately omitted from this deterministic example.

**Source code**

```{literalinclude} ../../../examples/5_webui/02_local_quantum_lab.py
:language: python
```

**Stdout**

```text
ghz probability sum: 1.0000000000
analytic error < 1e-10: True
w probability sum: 1.0000000000
analytic error < 1e-10: True
ramsey probability sum: 1.0000000000
analytic error < 1e-10: True
```

