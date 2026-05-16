# Hardware-Efficient Ansatz: Configuration Options

## Background and Theory

The Hardware-Efficient Ansatz (HEA) is a parameterised quantum circuit designed for near-term quantum devices. Unlike problem-specific ansätze (like UCCSD), HEA is hardware-adapted: gates and topology are chosen to match the native operations of the target device.

The HEA structure consists of $L$ repeated layers, where each layer contains:

1. **Single-qubit rotations** on every qubit: $R(\boldsymbol{\theta}) = \prod_i R_{\text{gate}_i}(\theta_i)$
2. **Entangling gates** following a connectivity topology: $U_{\text{ent}}(\boldsymbol{\phi}) = \prod_{(i,j) \in E} \text{Ent}_{i,j}(\phi)$

The variational parameters are the rotation angles and (for parametric entanglers) the entangling gate angles.

## Configurable Dimensions

The enhanced `hea()` function exposes three key dimensions:

### Rotation Gates

| Gate | Symbol | Parameters per qubit per layer | Notes |
|------|--------|-------------------------------|-------|
| RX | $R_x(\theta)$ | 1 | Rotation around X axis |
| RY | $R_y(\theta)$ | 1 | Rotation around Y axis |
| RZ | $R_z(\theta)$ | 1 | Rotation around Z axis |

**Default**: `[RZ, RY]` (backward compatible with previous version)

### Entangling Gates

| Gate | Symbol | Parameters per edge | Notes |
|------|--------|---------------------|-------|
| CNOT | $\text{CNOT}$ | 0 | Non-parametric |
| CZ | $\text{CZ}$ | 0 | Non-parametric |
| ISWAP | $\text{ISWAP}$ | 0 | Non-parametric |
| CRX | $\text{CRX}(\theta)$ | 1 | Parametric controlled-RX |
| CRY | $\text{CRY}(\theta)$ | 1 | Parametric controlled-RY |
| CRZ | $\text{CRZ}(\theta)$ | 1 | Parametric controlled-RZ |
| XX | $\text{XX}(\theta)$ | 1 | Parametric XX interaction |
| YY | $\text{YY}(\theta)$ | 1 | Parametric YY interaction |
| ZZ | $\text{ZZ}(\theta)$ | 1 | Parametric ZZ interaction |

### Entanglement Topologies

| Topology | Description | Edge count (4 qubits) |
|----------|-------------|------------------------|
| LINEAR | Chain: $(0,1), (1,2), (2,3)$ | $n-1$ |
| RING | Linear + wrap-around | $n$ |
| FULL | All-to-all | $\binom{n}{2}$ |
| STAR | Central qubit to all others | $n-1$ |
| BRICKWORK | Alternating pairs | Varies by layer |

## Running the Example

```bash
# Default: 4 qubits, depth 2
python examples/2_advanced/algorithms/hea_options.py

# Custom configuration
python examples/2_advanced/algorithms/hea_options.py --n-qubits 6 --depth 3
```

## Code Walkthrough

### 1. Rotation Gate Selection

```python
from uniqc.algorithms.core.ansatz import hea, RotationGate

# Default: RZ + RY
c = hea(n_qubits=4, depth=2)

# RX only
c = hea(n_qubits=4, depth=2, rotation_gates=["rx"])

# Full rotation (RX + RY + RZ)
c = hea(n_qubits=4, depth=2, rotation_gates=["rx", "ry", "rz"])
```

The number of rotation parameters is: `len(rotation_gates) × n_qubits × depth`

### 2. Entangling Gate Types

```python
from uniqc.algorithms.core.ansatz import hea, EntanglingGate

# Non-parametric gates (0 extra params)
c = hea(n_qubits=4, depth=2, entangling_gate="cnot")
c = hea(n_qubits=4, depth=2, entangling_gate="cz")

# Parametric gates (1 param per edge)
c = hea(n_qubits=4, depth=2, entangling_gate="xx", topology="ring")
```

For a 4-qubit ring topology:
- Non-parametric gates: 16 params (2 gates × 4 qubits × 2 layers)
- Parametric XX gates: 24 params (16 + 4 edges × 2 layers)

### 3. Topology Options

```python
from uniqc.algorithms.core.ansatz import EntanglementTopology

# Predefined topologies
c = hea(n_qubits=4, topology="linear")
c = hea(n_qubits=4, topology="ring")
c = hea(n_qubits=4, topology="full")
c = hea(n_qubits=4, topology="brickwork")

# Custom topology
c = hea(n_qubits=4, topology="custom", custom_edges=[(0, 1), (0, 2), (0, 3)])
```

### 4. Using `hea_param_count()`

```python
from uniqc.algorithms.core.ansatz import hea_param_count

# Pre-compute parameter count
n_params = hea_param_count(
    n_qubits=4,
    depth=2,
    rotation_gates=["rx", "ry", "rz"],
    entangling_gate="xx",
    topology="ring"
)
print(f"Need {n_params} parameters")

# Then allocate array
params = np.zeros(n_params)
c = hea(n_qubits=4, depth=2, rotation_gates=["rx", "ry", "rz"],
        entangling_gate="xx", topology="ring", params=params)
```

## Hardware-Aware Auto-Configuration

The `backend_info` parameter enables automatic selection of topology and gate based on hardware capabilities:

```python
from uniqc import get_backend

backend = get_backend("originq:Simulator")
c = hea(n_qubits=4, depth=2, backend_info=backend)
```

This automatically selects a topology that matches the device's qubit connectivity and chooses a native entangling gate from the backend's basis gates.

## Extensions

- **Noise-aware selection**: Choose gates/topologies that minimize error on specific hardware
- **Problem-specific encoding**: Use RZ gates to encode problem structure in phase
- **Circuit cutting**: Custom topology enables circuit cutting for devices with limited connectivity
- **Gradient computation**: Combine with parameter-shift rule for training

## References

1. Kandala, A. et al. (2017). "Hardware-efficient variational quantum eigensolver for small molecules and quantum magnets." *Nature* 549, 242-246. https://doi.org/10.1038/nature23879
