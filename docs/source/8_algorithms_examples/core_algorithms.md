# 核心量子算法

本节介绍教科书级量子算法：搜索（Grover）、相位估计（QPE）、振幅估计，
以及变分量子本征求解器（VQD）。这些是理解更复杂算法的前置基础。

## 示例

```{include} ../_generated/examples/2_advanced/algorithms__grover.md
```

```{include} ../_generated/examples/2_advanced/algorithms__qpe.md
```

```{include} ../_generated/examples/2_advanced/circuits__amplitude_estimation.md
```

```{include} ../_generated/examples/2_advanced/circuits__vqd.md
```

## 相关页面

- [线路构件](circuit_building_blocks.md) —— Grover oracle 等 QFragments 级构件
- [本地模拟](../1_basic_usage/simulation.md) —— 在本地后端上验证这些算法
- [Algorithm API 设计约定](../2_advanced/algorithm_design.md) —— oracle 类算法的输入约定
