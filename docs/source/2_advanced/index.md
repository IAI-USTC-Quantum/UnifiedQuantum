# 进阶教程

进阶部分覆盖编译内部机制、区域选择、变分量子算法、含噪 dummy 系统、calibration、
error mitigation、MPS 模拟器，以及 ``examples/2_advanced/`` 下完整的算法实现示例。

本页只列目录索引，仅在你已经熟悉 [基本用法](../1_basic_usage/index.md) 后再进入。

## 主题走读

```{toctree}
:maxdepth: 1

walkthrough
```

[进阶主题走读](walkthrough.md) 串联 7 个核心进阶主题（编译选项、RegionSelector、
变分算法、Dummy 系统、Calibration、QEM、MPS），每节都来自可重跑的示例脚本。

## 编译与基础设施

```{toctree}
:maxdepth: 1

compile_levels
compiler_options_region
adapter_architecture
opcode
circuit_analysis
```

## 模拟器

```{toctree}
:maxdepth: 1

mps_simulator
noise_simulation
```

## 算法、标定与测试

```{toctree}
:maxdepth: 1

algorithm_design
calibration
testing
```

## 算法实现示例（生成）

```{toctree}
:maxdepth: 1

algorithms
```

[算法实现示例](algorithms.md) 把 ``examples/2_advanced/`` 下所有 algorithms /
circuits / measurement / state_preparation / wk180 示例集中在一页里，便于按
"X 算法在 UnifiedQuantum 怎么写" 直接定位。
