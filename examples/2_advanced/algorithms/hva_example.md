# Hamiltonian Variational Ansatz (HVA)

## Background and Theory

The Hamiltonian Variational Ansatz (HVA) is designed for quantum simulation of systems with known Hamiltonian structure. Unlike generic ansätze (HEA), HVA respects the physical symmetries of the target system by alternating between exponentials of **commuting Hamiltonian groups**.

The HVA state is prepared as:

$$|\psi(\boldsymbol{\theta})\rangle = \prod_{l=1}^{p} \prod_{g=1}^{G} e^{-i\theta_{g,l} H_g} |\psi_{\text{HF}}\rangle$$

Where:
- $H_g$ are mutually commuting Hamiltonian groups: $[H_g, H_{g'}] = 0$
- $p$ is the depth (number of repetitions)
- $|\psi_{\text{HF}}\rangle$ is the Hartree-Fock initial state

### Advantages over HEA

| Aspect | HEA | HVA |
|--------|-----|-----|
| Hamiltonian structure | Ignored | Respected |
| Physical symmetries | May violate | Preserved |
| Parameter efficiency | General-purpose | Problem-specific |
| Convergence | Variable | Better for physical systems |

## Running the Example

```bash
# Default: 2 layers, 20 iterations
python examples/2_advanced/algorithms/hva_example.py

# Custom configuration
python examples/2_advanced/algorithms/hva_example.py -p 3 -n 30
```

## Code Walkthrough

### 1. Defining Commuting Hamiltonian Groups

```python
from uniqc.algorithms.core.ansatz import hva

# Group 1: Hopping terms (X and Y on same pairs commute)
hopping = [
    ("X0X1", 1.0),
    ("Y0Y1", 1.0),
]

# Group 2: Interaction term (ZZ commutes with itself)
interaction = [
    ("Z0Z1", 0.5),
]

groups = [hopping, interaction]
```

The key requirement is that terms within each group must commute: $[X_i X_j, Y_i Y_j] = 0$ and $[X_i X_j, X_k X_l] = 0$.

### 2. Building the HVA Circuit

```python
# Basic HVA: p=2 layers, auto-generated parameters
c = hva(groups, p=2)

# With explicit parameters
import numpy as np
params = np.random.uniform(0, np.pi, size=len(groups) * p)
c = hva(groups, p=2, params=params)
```

### 3. Hartree-Fock Initial State

```python
# HVA with Hartree-Fock state preparation
# hf_state specifies qubits in |1> (occupied orbitals)
c = hva(groups, p=2, hf_state=[0, 1])
```

The Hartree-Fock state encodes prior knowledge about the system ground state, which can significantly improve convergence.

### 4. Energy Evaluation

```python
from uniqc.algorithms.core.measurement import pauli_expectation

def energy(params):
    c = hva(groups, p=2, params=params)
    H = hopping + interaction  # Full Hamiltonian
    e = 0.0
    for pauli, coeff in H:
        e += coeff * pauli_expectation(c, pauli)
    return e
```

## When to Use HVA vs. HEA vs. UCCSD

| Algorithm | Use Case | Parameters |
|-----------|----------|------------|
| HEA | NISQ devices, generic optimization | $O(n \cdot d)$ |
| HVA | Quantum simulation, Hubbard models | $O(G \cdot p)$ |
| UCCSD | Molecular electronic structure | $O(n^4)$ |

### Choose HVA when:
- Hamiltonian has known group structure
- Commuting terms can be identified
- Physical symmetries matter
- Simulating condensed matter systems (Hubbard, Ising)

### Choose HEA when:
- Hardware constraints dominate
- Problem has no Hamiltonian structure
- Generic variational optimization needed

## Extensions

- **Adaptive HVA**: Grow depth based on gradient magnitude
- **Qubit-Mapped HVA**: Handle non-native qubit connectivities
- **Noise-Resilient HVA**: Choose groups minimizing noise sensitivity
- **Time-Evolving HVA**: Dynamic Hamiltonian evolution

## References

1. Wecker, D. et al. (2015). "Progress toward practical quantum variational algorithms." *Phys. Rev. A* 92, 060303.

2. Kivlichan, I.D. et al. (2018). "Quantum Simulation of Electronic Structure with Linear Depth and Connectivity." *Phys. Rev. Lett.* 120, 110501.

3. Sun, S. et al. (2021). "Quantum simulation of the Hubbard model with trapped ions." *PRX Quantum* 2, 020327.
