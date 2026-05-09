# Algorithm API design conventions

`uniqc.algorithms` exposes its primitives as **circuit fragments** —
self-contained `Circuit` objects you can assemble freely with
`Circuit.add_circuit()`. This page documents the four conventions used
across the package.

## 1. Variational ansätze — `_ansatz` suffix

Variational algorithms expose a parameterised **ansatz** factory that
returns a fresh :class:`~uniqc.circuit_builder.Circuit`.

```python
from uniqc.algorithms import hea, qaoa_ansatz, uccsd_ansatz, vqd_ansatz
import numpy as np

c = hea(n_qubits=4, n_layers=2, params=np.zeros(8))
```

Names: `hea`, `qaoa_ansatz`, `uccsd_ansatz`, `vqd_ansatz`.

## 2. State preparation — `_circuit` suffix

State-preparation primitives take an `n_qubits: int` (or `qubits`
list) and return a fresh `Circuit` containing only state-prep gates
(no measurements):

```python
from uniqc.algorithms import (
    qft_circuit, dicke_state_circuit, thermal_state_circuit,
    ghz_state, w_state, cluster_state,
)

c = qft_circuit(3)              # 3-qubit QFT
c = ghz_state(4)                # 4-qubit GHZ
```

The legacy in-place forms (e.g. `qft_circuit(circuit, qubits=...)`) are
kept as deprecated dispatch and emit a `DeprecationWarning`.

## 3. Oracular algorithms — input a `Circuit`

Algorithms that consume an oracle accept a `Circuit` as their first
argument and return a fresh `Circuit`:

```python
from uniqc.algorithms import (
    deutsch_jozsa_oracle, deutsch_jozsa_circuit,
    grover_oracle, grover_diffusion,
    amplitude_estimation_circuit,
)

oracle = deutsch_jozsa_oracle(qubits=[0, 1, 2], balanced=True)
dj     = deutsch_jozsa_circuit(oracle, qubits=[0, 1, 2])

ora    = grover_oracle(marked_state=5, qubits=[0, 1, 2])
diff   = grover_diffusion(qubits=[0, 1, 2])
```

## 4. Measurement — class-based interface

Measurement primitives are **classes**.  The constructor takes the
*clean* state-preparation circuit (no measurements); the class adds
basis rotations and measurements internally without mutating the input.

Each class exposes:

- `.get_readout_circuits() -> list[Circuit]` — circuits to actually run
- `.execute(backend="statevector", *, program_type="qasm", **kwargs)` —
  run them and return the post-processed result

```python
from uniqc.circuit_builder import Circuit
from uniqc.algorithms import (
    PauliExpectation, StateTomography, ClassicalShadow,
    BasisRotationMeasurement,
)

c = Circuit()
c.h(0); c.cx(0, 1)

value = PauliExpectation(c, "ZZ").execute("statevector")
rho   = StateTomography(c, shots=8192).execute()
```

The free-function APIs (`pauli_expectation`, `state_tomography`,
`classical_shadow`, `basis_rotation_measurement`) remain available as
thin convenience wrappers but new code should prefer the class form.

## 5. `_example` helpers

Every algorithm module additionally exports a `<name>_example()`
function intended for documentation and quick smoke-tests.  They are
**not** part of `__all__` — import them via the full module path:

```python
from uniqc.algorithms.core.circuits.qft import qft_example
c = qft_example()
```
