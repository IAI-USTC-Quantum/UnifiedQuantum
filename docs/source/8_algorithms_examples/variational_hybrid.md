# 变分与混合算法

变分量子算法（VQE、QAOA）和量子机器学习模型是 NISQ 时代最实用的范式。
本节分别展示纯经典优化器驱动版本和 PyTorch 集成版本，以及量子‑经典混合模型
和量子神经网络 / 卷积分类器。

## VQE / QAOA

```{include} ../_generated/examples/2_advanced/algorithms__vqe.md
```

```{include} ../_generated/examples/2_advanced/algorithms__vqe_pytorch.md
```

```{include} ../_generated/examples/2_advanced/algorithms__qaoa.md
```

```{include} ../_generated/examples/2_advanced/algorithms__qaoa_pytorch.md
```

```{include} ../_generated/examples/2_advanced/algorithms__qaoa_variants.md
```

```{include} ../_generated/examples/2_advanced/algorithms__adapt_vqe.md
```

## Ansatz 配置

```{include} ../_generated/examples/2_advanced/algorithms__hea_options.md
```

```{include} ../_generated/examples/2_advanced/algorithms__hva_example.md
```

```{include} ../_generated/examples/2_advanced/algorithms__parameters_demo.md
```

```{include} ../_generated/examples/2_advanced/algorithms__parametric_originir_roundtrip.md
```

## 量子‑经典混合模型

```{include} ../_generated/examples/2_advanced/algorithms__hybrid_model.md
```

```{include} ../_generated/examples/2_advanced/algorithms__qnn_classifier.md
```

```{include} ../_generated/examples/2_advanced/algorithms__qcnn_classifier.md
```

## 相关页面

- [PyTorch 集成](../1_basic_usage/pytorch.md) —— 本页 Torch 版示例的底层 API
- [参数化线路](../1_basic_usage/circuit.md) —— `PARAM` 符号参数与 round-trip
- [Algorithm API 设计约定](../2_advanced/algorithm_design.md) —— ansatz 命名与参数管理约定
- [本地模拟](../1_basic_usage/simulation.md) —— 训练循环中的模拟器选择
