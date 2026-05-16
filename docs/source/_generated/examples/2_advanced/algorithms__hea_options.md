### Hardware-Efficient Ansatz (HEA) -- Configuration Options.

*Source*: ``examples/2_advanced/algorithms/hea_options.py``  
*Status*: **pass**

Demonstrates:
  * Configurable rotation gates (RX, RY, RZ)
  * Configurable entangling gates (CNOT, CZ, CRX, XX)
  * Entanglement topologies (LINEAR, RING, FULL, BRICKWORK)
  * Parameter counting with hea_param_count()

Usage:
    python hea_options.py [--n-qubits N] [--depth L]

References:
    Kandala, A. et al. (2017). "Hardware-efficient variational quantum
    eigensolver for small molecules and quantum magnets."
    Nature 549, 242-246. https://doi.org/10.1038/nature23879

**Source code**

```{literalinclude} ../../../examples/2_advanced/algorithms/hea_options.py
:language: python
```

**Stdout**

```text

============================================================
HEA Configuration Demo (n_qubits=4, depth=2)
============================================================
============================================================
Demo 1: Rotation Gate Configurations
============================================================

  Default (RZ + RY):
    Parameters: 16

  RZ+RY circuit:
    Qubits used: 4
    Gate count: 24

  RX only:
    Parameters: 8

  RX circuit:
    Qubits used: 4
    Gate count: 16

  RX + RY + RZ (full):
    Parameters: 24

  Full rotation circuit:
    Qubits used: 4
    Gate count: 32

  RZ+RY statevector norm: 1.0000000000

  RX statevector norm: 1.0000000000

  RX+RY+RZ statevector norm: 1.0000000000

============================================================
Demo 2: Entangling Gate Configurations
============================================================

  Non-parametric gates:
    CNOT    :  16 params

  CNOT circuit:
    Qubits used: 4
    Gate count: 24
    CZ      :  16 params

  CZ circuit:
    Qubits used: 4
    Gate count: 24
    ISWAP   :  16 params

  ISWAP circuit:
    Qubits used: 4
    Gate count: 24

  Parametric gates (extra params per edge):
    CRX     :  24 params

  CRX circuit:
    Qubits used: 4
    Gate count: 24
    XX      :  24 params

  XX circuit:
    Qubits used: 4
    Gate count: 24
    YY      :  24 params

  YY circuit:
    Qubits used: 4
    Gate count: 24
    ZZ      :  24 params

  ZZ circuit:
    Qubits used: 4
    Gate count: 24

  CNOT statevector norm: 1.0000000000

  CZ statevector norm: 1.0000000000

  CRX statevector norm: 1.0000000000

  XX statevector norm: 1.0000000000

============================================================
Demo 3: Entanglement Topologies
============================================================

  LINEAR    :
    Parameters: 16

  LINEAR circuit:
    Qubits used: 4
    Gate count: 22

  RING      :
    Parameters: 16

  RING circuit:
    Qubits used: 4
    Gate count: 24

  FULL      :
    Parameters: 16

  FULL circuit:
    Qubits used: 4
    Gate count: 28

  STAR      :
    Parameters: 16

  STAR circuit:
    Qubits used: 4
    Gate count: 22

  BRICKWORK :
    Parameters: 16

  BRICKWORK circuit:
    Qubits used: 4
    Gate count: 19

  CUSTOM (user-defined edges):
    Edges: [(0, 1), (0, 2), (0, 3)]
    Parameters: 16

  Custom circuit:
    Qubits used: 4
    Gate count: 22

============================================================
Demo Complete
============================================================
```

