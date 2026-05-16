# Symbolic Parameters for Variational Circuits

## Background and Theory

Traditional variational quantum algorithms use raw numpy arrays for parameters. While functional, this approach has limitations:

1. **No symbolic tracking**: Parameter names are lost after construction
2. **Gradient bookkeeping**: Difficult to map gradients back to specific parameters
3. **Debugging**: Hard to identify which parameter caused issues

The `Parameter` and `Parameters` classes in `uniqc.circuit_builder.parameter` address these issues by providing:

- **Named parameters**: Each parameter has a unique name (e.g., `theta_0`, `gamma_2`)
- **Symbolic expressions**: Arithmetic operations produce sympy expressions
- **Binding workflow**: Parameters can be bound, unbound, and rebound to new values

### Parameter vs. ndarray

| Aspect | ndarray | Parameter |
|---------|---------|-----------|
| Creation | `np.zeros(n)` | `Parameters("theta", n)` |
| Naming | Index only | Name + index |
| Binding | Direct assignment | `bind(values)` method |
| Arithmetic | Numeric only | Symbolic expressions |
| Gradient tracking | Manual index mapping | Built-in name lookup |

## Running the Example

```bash
python examples/2_advanced/algorithms/parameters_demo.py
```

## Code Walkthrough

### 1. Auto-Generation (params=None)

```python
from uniqc.algorithms.core.ansatz import hea

# When params=None, ansatz functions auto-generate Parameters
c = hea(n_qubits=4, depth=2)

# Access the auto-generated parameters
print(c._params.name)       # "theta_hea"
print(len(c._params))      # 16
print(c._params.names)      # ['theta_hea_0', ..., 'theta_hea_15']
```

Auto-generation uses a consistent naming convention:
- HEA: `theta_hea_0`, `theta_hea_1`, ...
- QAOA: `betas_qaoa_0`, `gammas_qaoa_0`, ...
- HVA: `theta_hva_0`, `theta_hva_1`, ...
- UCCSD: `theta_uccsd_0`, `theta_uccsd_1`, ...

### 2. Pre-computing Parameter Count

```python
from uniqc.algorithms.core.ansatz import hea_param_count

# Determine parameter count before allocation
n_params = hea_param_count(
    n_qubits=4,
    depth=2,
    rotation_gates=["rx", "ry", "rz"],
    entangling_gate="xx",
    topology="ring"
)
print(f"Need {n_params} parameters")
```

This is essential for proper memory allocation and validation.

### 3. Manual Binding Workflow

```python
from uniqc.circuit_builder.parameter import Parameters
from uniqc.algorithms.core.ansatz import hea

# Step 1: Determine count
n_params = hea_param_count(4, 2)

# Step 2: Create Parameters object
params = Parameters("my_ansatz", size=n_params)

# Step 3: Bind values
values = [0.1 * (i + 1) for i in range(n_params)]
params.bind(values)

# Step 4: Use in circuit
c = hea(4, 2, params=params)

# Step 5: Verify
print(f"circuit._params is params: {c._params is params}")

# Step 6: Rebind for new optimization
params.bind([0.5] * n_params)
c2 = hea(4, 2, params=params)
```

### 4. Symbolic Arithmetic

```python
from uniqc.circuit_builder.parameter import Parameter

theta = Parameter("theta")
phi = Parameter("phi")

# Arithmetic creates sympy expressions
expr1 = theta + phi / 2
expr2 = theta * 2 - phi
expr3 = -theta

# Bind values and evaluate
theta.bind(1.0)
phi.bind(2.0)
print(float(expr1.evalf()))  # 2.0
print(float(expr2.evalf()))  # 0.0
```

## Integration with Ansatz Functions

| Function | Accepts Parameters | Auto-generates |
|----------|-------------------|----------------|
| `hea()` | Yes | Yes |
| `qaoa_ansatz()` | Yes (betas/gammas) | Yes |
| `hva()` | Yes | Yes |
| `uccsd_ansatz()` | Yes | Yes |

## Extensions

- **Parameter-shift gradients**: Map gradient indices to parameter names
- **Batch optimization**: Share parameters across multiple circuits
- **Parameter constraints**: Use symbolic expressions for bounds
- **Gradient-free optimization**: Evaluate with different bound values

## References

- sympy documentation: https://docs.sympy.org/latest/
- PennyLane parameter management: https://pennylane.ai/
