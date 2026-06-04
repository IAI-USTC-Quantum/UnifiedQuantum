### 02 — Local simulation paths

*Source*: ``examples/1_basic_usage/02_local_simulation.py``  
*Status*: **pass**

UnifiedQuantum 自带几条本地模拟路径：

* ``Simulator`` — 默认 statevector 模拟器；
* MPS 后端（线性拓扑 + 中等纠缠下可扩展到上百比特）—— 见
  ``examples/2_advanced/01_mps_simulator.py``；
* C++ 后端 ``uniqc_cpp`` — 自动作为 ``Simulator`` 的加速实现（如果已编译）。

这里只演示最直接的 ``simulate_pmeasure`` 与 ``simulate_shots``。

**Source code**

```{literalinclude} ../../../examples/1_basic_usage/02_local_simulation.py
:language: python
```

**Stdout**

```text
== probabilities ==
  |000>: 0.5000
  |111>: 0.5000
== shots ==
{0: 1005, 7: 995}
```

