### 04 — Dummy chip noise: ``dummy:<platform>:<backend>``

*Source*: ``examples/2_advanced/04_dummy_chip_noise.py``  
*Status*: **pass**

``dummy:<platform>:<backend>`` 是规则型 backend id：**它不会出现在 backend 列表**，
但提交时会先按真实 backend compile/transpile，然后用本地 dummy adapter 注入对应芯片
的标定噪声。常用形态：

* ``dummy:local:simulator`` — 完全无约束、无噪声；
* ``dummy:local:virtual-line-N`` / ``virtual-grid-RxC`` — 虚拟拓扑、无噪声；
* ``dummy:local:mps-linear-N[:chi=K[:cutoff=E]]`` — 线性 MPS 引擎；
* ``dummy:<platform>:<backend>`` — 真芯片拓扑 + 标定噪声（需要芯片缓存）。

最后一种需要先用 ``uniqc backend update --platform originq`` 等命令把芯片缓存
拉下来；本例只演示三种 ``dummy:local:*`` 形态。

**Source code**

```{literalinclude} ../../../examples/2_advanced/04_dummy_chip_noise.py
:language: python
```

**Stdout**

```text
== dummy:local:simulator ==
  description:     Unconstrained noiseless local simulator
  topology:        None
  simulator_kwargs: None
  counts:          UnifiedResult(counts={'000': 128, '111': 128}, probabilities={'000': 0.5, '111': 0.5}, shots=256, platform='dummy', task_id='uqt_a9a6bce0f0594aebae738458ac1eaeef', backend_name='dummy:local:simulator', execution_time=None, error_message=None)
== dummy:local:virtual-line-3 ==
  description:     Noiseless virtual 3-qubit line topology
  topology:        [[0, 1], [1, 2]]
  simulator_kwargs: None
  counts:          UnifiedResult(counts={'000': 128, '111': 128}, probabilities={'000': 0.5, '111': 0.5}, shots=256, platform='dummy', task_id='uqt_4b3dc39390c04f818a8fa7ee22f7ce0e', backend_name='dummy:local:virtual-line-3', execution_time=None, error_message=None)
== dummy:local:mps-linear-3:chi=8 ==
  description:     Noiseless MPS simulator on a 3-qubit linear chain, chi=8
  topology:        [[0, 1], [1, 2]]
  simulator_kwargs: {'chi_max': 8}
  counts:          UnifiedResult(counts={'111': 124, '000': 132}, probabilities={'111': 0.484375, '000': 0.515625}, shots=256, platform='dummy', task_id='uqt_621a4cfb987743a6836423ca588b827c', backend_name='dummy:local:mps-linear-3:chi=8', execution_time=None, error_message=None)
```

