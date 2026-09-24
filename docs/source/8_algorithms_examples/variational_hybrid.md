# 变分与混合算法

变分量子算法（{py:func}`VQE <uniqc.algorithms.core.ansatz.uccsd.uccsd_ansatz>`、{py:func}`QAOA <uniqc.algorithms.core.ansatz.qaoa_ansatz.qaoa_ansatz>`）
和量子机器学习模型是 NISQ 时代最实用的范式。
本节分别展示纯经典优化器驱动版本和 {py:class}`PyTorch 集成 <uniqc.torch_adapter.quantum_layer.QuantumLayer>` 版本，以及量子‑经典混合模型
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
