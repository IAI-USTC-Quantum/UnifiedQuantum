### Symbolic Parameters for Variational Circuits.

*Source*: ``examples/2_advanced/algorithms/parameters_demo.py``  
*Status*: **pass**

Demonstrates:
  * Auto-generation of Parameters when params=None
  * Manual binding workflow with Parameters objects
  * Pre-computing parameter counts with hea_param_count()
  * Symbolic arithmetic with Parameter objects

Usage:
    python parameters_demo.py

**Source code**

```{literalinclude} ../../../examples/2_advanced/algorithms/parameters_demo.py
:language: python
```

**Stdout**

```text

============================================================
Symbolic Parameters Demo
============================================================
============================================================
Demo 1: Auto-Generated Parameters
============================================================

  Calling hea(n_qubits=4, depth=2) without params:

  Circuit._params type: Parameters
  Parameters name: theta_hea
  Parameters count: 16
  Parameter names: ['theta_hea_0', 'theta_hea_1', 'theta_hea_2', 'theta_hea_3', 'theta_hea_4', 'theta_hea_5', 'theta_hea_6', 'theta_hea_7', 'theta_hea_8', 'theta_hea_9', 'theta_hea_10', 'theta_hea_11', 'theta_hea_12', 'theta_hea_13', 'theta_hea_14', 'theta_hea_15']
  First 4 values: ['4.0021', '1.6951', '0.2574', '0.1038']

  QAOA auto-generated parameters:
    betas: betas_qaoa, len=2
    gammas: gammas_qaoa, len=2

============================================================
Demo 2: Pre-computing Parameter Counts
============================================================

  For n_qubits=4, depth=2:

  Configuration                  Parameters  
  ------------------------------------------
  RZ+RY (default)                16          
  RX only                        8           
  RX+RY+RZ                       24          
  CNOT (default)                 16          
  CZ                             16          
  XX (parametric)                24          
  Linear topology                16          
  Full topology                  16          

  Use hea_param_count() to determine array size before building:

  n_params = hea_param_count(4, 2, rotation_gates=['rx', 'ry'])
  # n_params = 16
  params = np.zeros(n_params)

============================================================
Demo 3: Manual Parameters Binding
============================================================

  Step 1: Determine parameter count
    n_params = hea_param_count(4, 2) = 16

  Step 2: Create Parameters object
    params = Parameters('my_ansatz_params', size=16)
    names: ['my_ansatz_params_0', 'my_ansatz_params_1', 'my_ansatz_params_2', 'my_ansatz_params_3', 'my_ansatz_params_4', 'my_ansatz_params_5', 'my_ansatz_params_6', 'my_ansatz_params_7', 'my_ansatz_params_8', 'my_ansatz_params_9', 'my_ansatz_params_10', 'my_ansatz_params_11', 'my_ansatz_params_12', 'my_ansatz_params_13', 'my_ansatz_params_14', 'my_ansatz_params_15']

  Step 3: Bind values
    params.bind([0.1, 0.2, ..., 1.6])  # 16 values
    Bound: True

  Step 4: Build circuit
    circuit = hea(4, 2, params=params)
    circuit._params is params: True

  Step 5: Verify circuit
    Statevector norm: 1.0000000000

  Step 6: Rebind for new optimization
    params.bind([0.5, 0.5, ..., 0.5])  # 16 values
    Rebuilt circuit successfully

============================================================
Demo 4: Symbolic Arithmetic
============================================================

  Creating parameters:
    theta = Parameter('theta')
    phi = Parameter('phi')

  Arithmetic expressions (sympy):
    theta + phi/2 = phi/2 + theta
    theta*2 - phi = -phi + 2*theta
    -theta = -theta

  After binding theta=1.0, phi=2.0:
    theta + phi/2 = 2.0
    theta*2 - phi = 0.0

  Parameters array:
    params[0].name = 'alpha_0', value = 0.5
    params[1].name = 'alpha_1', value = 1.0
    params[2].name = 'alpha_2', value = 1.5

============================================================
Demo Complete
============================================================
```

