# QAOA Variants: XY Mixer, Warm-Start, and MA-QAOA

## Background and Theory

The Quantum Approximate Optimization Algorithm (QAOA) solves combinatorial optimization problems by alternating between a **cost Hamiltonian** $H_C$ (encoding the objective) and a **mixer Hamiltonian** $H_M$ (exploring the solution space):

$$|\psi(\boldsymbol{\gamma}, \boldsymbol{\beta})\rangle = \prod_{l=1}^{p} e^{-i\beta_l H_M} e^{-i\gamma_l H_C} |s\rangle$$

### Standard QAOA

The standard mixer is $H_M = \sum_i X_i$, which drives transitions between all basis states. This works well for unconstrained problems but may be inefficient for constrained optimization.

### XY Mixer

The XY mixer preserves the number of excitations (useful for problems with Hamming weight constraints):

$$H_M^{\text{XY}} = \sum_{\langle i,j \rangle} (X_i X_j + Y_i Y_j)$$

This mixer is especially useful for:
- **Portfolio optimization** (fixed number of assets)
- **Molecular geometry** (fixed bond lengths)
- **Graph coloring** (exactly one color per vertex)

### Warm-Start QAOA

Warm-start QAOA initializes the quantum state from a good classical solution, reducing the distance the quantum optimizer must travel:

$$|s\rangle \rightarrow |\psi_{\text{classical}}\rangle$$

This provides a better starting point and can accelerate convergence.

### MA-QAOA (Multi-Angle)

Standard QAOA shares one $\gamma$ and one $\beta$ per layer. MA-QAOA increases expressivity by assigning:
- **One $\gamma$ per Hamiltonian term**: captures term-specific structure
- **One $\beta$ per qubit**: enables finer control over the mixer

## Running the Example

```bash
# Default: 2 layers, 4-node graph
python examples/2_advanced/algorithms/qaoa_variants.py

# Custom configuration
python examples/2_advanced/algorithms/qaoa_variants.py -p 3 -n 6
```

## Code Walkthrough

### 1. XY Mixer for Constrained Optimization

```python
from uniqc.algorithms.core.ansatz import qaoa_ansatz

# Define Hamiltonian (MaxCut on a ring)
H = [("Z0Z1", 0.5), ("Z1Z2", 0.5), ("Z2Z3", 0.5), ("Z3Z0", 0.5)]

# Standard QAOA
c_standard = qaoa_ansatz(H, p=2)

# XY Mixer QAOA (preserves excitation number)
c_xy = qaoa_ansatz(H, p=2, mixer="xy")
```

The XY mixer applies $R_{XX}(2\beta) + R_{YY}(2\beta)$ on each edge, preserving the Hamming weight.

### 2. Warm-Start QAOA

```python
from uniqc import Circuit

# Build a custom initial state from a greedy solution
warm_state = Circuit()
for i in range(n_nodes):
    if greedy_solution[i] == 1:
        warm_state.x(i)

# Warm-start QAOA
c_warm = qaoa_ansatz(H, p=2, initial_state=warm_state)
```

The warm-start state can be any basis state (e.g., from a classical algorithm).

### 3. MA-QAOA (Multi-Angle)

```python
# MA-QAOA: per-term gammas + per-qubit betas
# For n_terms = 4, n_qubits = 4, p = 2:
#   gammas: 4 × 2 = 8 (one per term per layer)
#   betas: 4 × 2 = 8 (one per qubit per layer)
#   Total: 16 parameters

c_ma = qaoa_ansatz(H, p=2, multi_angle=True)

# Compare with standard QAOA:
#   betas: 2, gammas: 2 → 4 parameters
```

## Parameter Comparison

| Variant | Parameters per layer | Total (p layers) | Use case |
|---------|---------------------|------------------|----------|
| Standard QAOA | 2 (β, γ) | 2p | Unconstrained MaxCut, general optimization |
| XY Mixer | 2 (β, γ) | 2p | Constrained problems, fixed Hamming weight |
| Warm-Start | 2 (β, γ) | 2p | When good classical solution available |
| MA-QAOA | n_terms + n_qubits | (n_terms + n_qubits)p | Maximum expressivity |

## Extensions

- **Grover Mixer**: $H_M = G - I$ for quantum-enhanced search
- **FRQI Mixer**: For combinatorial auction problems
- **Recursive QAOA (RQAOA)**: Hierarchical problem decomposition
- **Adaptive QAOA**: Layer-by-layer optimization with validation

## References

1. Hadfield, S. et al. (2019). "From the Quantum Approximate Optimization Algorithm to a Quantum Alternating Operator Ansatz." arXiv:1709.03489.

2. Egger, D.J. et al. (2021). "Warm-starting quantum optimization." arXiv:2009.10095.

3. Hadir, M. et al. (2023). "Multi-Angle Quantum Approximate Optimization Algorithm." arXiv:2305.04881.
