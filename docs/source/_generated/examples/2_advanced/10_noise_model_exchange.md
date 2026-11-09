### 版本化噪声模型交换与含噪 VM 的 QRAM/QPU 寻址

*Source*: ``examples/2_advanced/10_noise_model_exchange.py``  
*Status*: **pass**

Versioned noise-model exchange: import, 3-layer QRAM, QPU addressing, mitigation.

Demonstrates the noise-bridge capability added this round:

* generate a synthetic ``nlearn.noise-model.v1`` exchange file
  (WK_C180-scale channels, ``data_class: synthetic`` — not hardware data);
* import it into the noisy VM (density-operator simulator) via
  ``load_noise_model``;
* run the 3-layer (8-entry) QRAM basis lookup and the QPU-superposition
  addressing case;
* mitigate the data-register readout through the unified ``ReadoutEM``
  interface, calibrated on the same noisy VM.

Everything runs locally; no cloud task is submitted. Real historical noise
data arrives as ``hardware_archive``/``historical_replay`` exchange files
produced by the noise-learning product — same import path, no code coupling.

Usage:
    python 10_noise_model_exchange.py

**Source code**

```{literalinclude} ../../../examples/2_advanced/10_noise_model_exchange.py
:language: python
```

**Stdout**

```text
imported nlearn.noise-model.v1 model sha256=b4f3dce4fc68...
data_class=synthetic  chain=[0, 1, 2, 3, 4]

== 3-layer QRAM basis lookup (address=5, shots=500) ==
expected value      : 2 (10)
raw accuracy        : 0.932 (top outcome 10)
mitigated accuracy  : 0.958 (top outcome 10)
noisy counts        : {'00': 11, '01': 1, '10': 466, '11': 22}
mitigated counts    : {'00': 5, '01': 0, '10': 478, '11': 16}

== QPU superposition addressing (shots=500) ==
ideal distribution  : {'0': 0.25, '1': 0.25, '2': 0.25, '3': 0.25}
raw fidelity        : 0.9993
mitigated fidelity  : 0.9995
```

