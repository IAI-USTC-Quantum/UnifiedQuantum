### 07 — Matrix-product-state simulator on a long linear chain

*Source*: ``examples/2_advanced/07_mps_simulator.py``  
*Status*: **pass**

MPS 引擎是一个线性拓扑、无噪声、能扩展到上百比特的模拟器（前提是中等纠缠）。两种
入口：

* ``MPSSimulator`` 直接 API；
* ``submit_task(backend="dummy:local:mps-linear-N:chi=K:cutoff=E:seed=S")`` 通过统一的
  任务接口（参数解析见 ``resolve_dummy_backend``）。

**Source code**

```{literalinclude} ../../../examples/2_advanced/07_mps_simulator.py
:language: python
```

**Stdout**

```text
== Direct MPSSimulator (N=32) ==
  observed keys: [0, 4294967295]
  total shots:   400
  max bond dim:  2

== dummy:local:mps-linear-32 backend (chi=8, forces truncation) ==
  result: UnifiedResult(counts={'00000000000000000000000000000000': 195, '11111111111111111111111111111111': 205}, probabilities={'00000000000000000000000000000000': 0.4875, '11111111111111111111111111111111': 0.5125}, shots=400, platform='dummy', task_id='uqt_ac5a4f69e5bb4e718b6603242b52ad84', backend_name='dummy:local:mps-linear-32:chi=8:cutoff=1e-10', execution_time=None, error_message=None)

== Parameter parsing ==
  identifier:        dummy:local:mps-linear-8:chi=16:cutoff=1e-8:seed=7
  available_qubits:  [0, 1, 2, 3, 4, 5, 6, 7]
  simulator_kwargs:  {'chi_max': 16, 'svd_cutoff': 1e-08, 'seed': 7}
```

