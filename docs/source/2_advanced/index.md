# 进阶教程

进阶部分覆盖编译内部、区域选择、变分量子算法、含噪 dummy 系统、calibration、error
mitigation、MPS 模拟器。每一节都对应一个可运行的 ``examples/2_advanced/*.py``。

## 1. 编译内部选项

```{include} ../_generated/examples/2_advanced/01_compile_options.md
```

## 2. RegionSelector：在芯片上挑选高保真度子区域

```{include} ../_generated/examples/2_advanced/02_region_selector.md
```

## 3. 变分量子算法（小型 QAOA）

```{include} ../_generated/examples/2_advanced/03_variational_qaoa.md
```

完整的 VQA 训练循环示例：

* [`examples/3_best_practices/07_variational_circuit.py`](../3_best_practices/index.md)
* [`examples/3_best_practices/08_torch_quantum_training.py`](../3_best_practices/index.md)

## 4. Dummy 系统：noiseless、virtual-topology、chip-noise

UnifiedQuantum 的 dummy 系统通过 backend id 文法区分三种语义：

| id | 含义 |
|----|------|
| ``dummy`` / ``dummy:local:simulator`` | 完全无约束、无噪声 |
| ``dummy:local:virtual-line-N`` | 长度 N 的虚拟线性拓扑、无噪声 |
| ``dummy:local:virtual-grid-RxC`` | R×C 的虚拟网格拓扑、无噪声 |
| ``dummy:local:mps-linear-N[:chi=K[:cutoff=E]]`` | MPS 引擎，线性拓扑 |
| ``dummy:<platform>:<backend>`` | 复用真实 backend 拓扑 + 标定噪声，先 compile/transpile 再本地含噪执行 |

```{include} ../_generated/examples/2_advanced/04_dummy_chip_noise.md
```

## 5. Calibration：1q / 2q / parallel-2q XEB + readout

```{include} ../_generated/examples/2_advanced/05_calibration_xeb.md
```

完整 workflow 见 ``uniqc calibrate xeb`` / ``uniqc calibrate readout`` /
``uniqc calibrate pattern``，结果统一缓存到 ``~/.uniqc/calibration_cache/``，
带 ISO-8601 时间戳和 TTL 新鲜度检查。

## 6. Error mitigation：M3 + ReadoutEM

```{include} ../_generated/examples/2_advanced/06_qem_m3.md
```

QEM 模块当前覆盖：

* {py:class}`uniqc.M3Mitigator` —— 多比特读取误差线性反演（M3 风格）；
* {py:class}`uniqc.ReadoutEM` —— 自动从 calibration cache 读校准、强制 TTL 检查；
* {py:mod}`uniqc.qem.zne` —— 零噪声外推（实验性）。

## 7. MPS 模拟器（长链可扩展）

```{include} ../_generated/examples/2_advanced/07_mps_simulator.md
```

MPS 引擎适合**线性拓扑 + 中等纠缠**的大规模线路，可扩展到上百比特。``chi`` 决定
最大键维（精度↑ 内存↑ 时间↑），``cutoff`` 是 SVD 截断阈值。
