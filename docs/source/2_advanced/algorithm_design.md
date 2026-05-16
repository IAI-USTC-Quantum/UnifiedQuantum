# Algorithm API design conventions

`uniqc.algorithms` exposes its primitives as **circuit fragments** —
self-contained `Circuit` objects you can assemble freely with
`Circuit.add_circuit()`. This page documents the four conventions used
across the package.

## 1. Variational ansätze — `_ansatz` suffix

Variational algorithms expose a parameterised **ansatz** factory that
returns a fresh :class:`~uniqc.circuit_builder.Circuit`.

```python
from uniqc.algorithms import hea, hva, qaoa_ansatz, uccsd_ansatz, vqd_ansatz
import numpy as np

# Default HEA (backward-compatible)
c = hea(n_qubits=4, depth=2, params=np.zeros(16))

# Enhanced HEA: custom rotations, gates, and topology
c = hea(n_qubits=4, depth=2,
        rotation_gates=["rx", "ry", "rz"],
        entangling_gate="cz",
        topology="linear")

# Parametric entangling gate (extra params per edge)
c = hea(n_qubits=4, depth=2, entangling_gate="xx", topology="ring")

# HVA with commuting Hamiltonian groups
groups = [[("X0X1", 1.0), ("Y0Y1", 1.0)], [("Z0Z1", 0.5)]]
c = hva(groups, p=2)
```

Names: `hea`, `hva`, `qaoa_ansatz`, `uccsd_ansatz`, `vqd_ansatz`.

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

## 6. Parameter management

All ansatz functions accept either `np.ndarray` (backward-compatible) or
`Parameters` objects for symbolic parameter management.

```python
from uniqc.circuit_builder import Parameters
from uniqc.algorithms.core.ansatz import hea, hea_param_count

# Auto-generation: when params=None, a named Parameters object is created
c = hea(n_qubits=4, depth=2)
print(c._params.name)  # "theta_hea"
print(len(c._params))  # 16

# Manual Parameters: create, bind, and use
n_params = hea_param_count(n_qubits=4, depth=2,
                          rotation_gates=["rx", "ry", "rz"])
params = Parameters("my_ansatz", size=n_params)
params.bind([0.1] * n_params)
c = hea(n_qubits=4, depth=2, params=params)

# QAOA uses separate betas and gammas
c = qaoa_ansatz(H, p=2)
print(c._params["betas"].name)  # "betas_qaoa"
print(c._params["gammas"].name) # "gammas_qaoa"
```

Benefits of `Parameters`:
- Named parameters for debugging and gradient tracking
- Symbolic arithmetic via sympy expressions
- Rebindable values for multiple optimization runs
- See: `examples/2_advanced/algorithms/parameters_demo.py`
