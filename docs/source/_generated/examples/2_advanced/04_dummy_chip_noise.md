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
  counts:          UnifiedResult(counts={'000': 128, '111': 128}, probabilities={'000': 0.5, '111': 0.5}, shots=256, platform='dummy', task_id='uqt_bd0ce20a8ce24b5884c00cbf09b17af4', backend_name='dummy:local:simulator', execution_time=None, error_message=None)
== dummy:local:virtual-line-3 ==
  description:     Noiseless virtual 3-qubit line topology
  topology:        [[0, 1], [1, 2]]
  simulator_kwargs: None
  counts:          UnifiedResult(counts={'000': 128, '111': 128}, probabilities={'000': 0.5, '111': 0.5}, shots=256, platform='dummy', task_id='uqt_aaf3f16ea63443d081a443c42b7c9490', backend_name='dummy:local:virtual-line-3', execution_time=None, error_message=None)
== dummy:local:mps-linear-3:chi=8 ==
  description:     Noiseless MPS simulator on a 3-qubit linear chain, chi=8
  topology:        [[0, 1], [1, 2]]
  simulator_kwargs: {'chi_max': 8}
  counts:          UnifiedResult(counts={'000': 129, '111': 127}, probabilities={'000': 0.50390625, '111': 0.49609375}, shots=256, platform='dummy', task_id='uqt_ab08754026be458c84ce67a5408ccf61', backend_name='dummy:local:mps-linear-3:chi=8', execution_time=None, error_message=None)
```

