### 03 — Variational quantum algorithm: a tiny QAOA loop

*Source*: ``examples/2_advanced/03_variational_qaoa.py``  
*Status*: **pass**

最小可执行的 QAOA 演示：固定 1 层、单参数对，扫两个角度找最优。
真正的 VQA 训练循环在 ``examples/3_best_practices/07_variational_circuit.py``
和 ``examples/3_best_practices/08_torch_quantum_training.py``。

**Source code**

```{literalinclude} ../../../examples/2_advanced/03_variational_qaoa.py
:language: python
```

**Stdout**

```text
gamma=0.20 beta=0.20 <ZZ>=+0.2109
gamma=0.20 beta=0.40 <ZZ>=+0.4023
gamma=0.20 beta=0.60 <ZZ>=+0.2031
gamma=0.40 beta=0.20 <ZZ>=+0.4609
gamma=0.40 beta=0.40 <ZZ>=+0.7383
gamma=0.40 beta=0.60 <ZZ>=+0.5156
gamma=0.60 beta=0.20 <ZZ>=+0.6797
gamma=0.60 beta=0.40 <ZZ>=+0.9297
gamma=0.60 beta=0.60 <ZZ>=+0.6406
best: (0.2, 0.6, 0.203125)
```

