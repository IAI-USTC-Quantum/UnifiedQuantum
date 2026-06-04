### 11 — 原生 Torch 训练（不依赖 TorchQuantum）

*Source*: ``examples/3_best_practices/11_native_torch_training.py``  
*Status*: **pass**

使用 UnifiedQuantum 原生 ``expectation()`` 函数进行量子-经典混合训练。

无需 TorchQuantum 依赖——梯度通过纯 PyTorch 的态矢量模拟自动传播。
本示例演示三种参数风格：``has_param``、``param_dict``、直接传入 tensor。

**Source code**

```{literalinclude} ../../../examples/3_best_practices/11_native_torch_training.py
:language: python
```

**Stdout**

```text
=== 风格 1: has_param ===
  初始能量: -0.8093
  最终能量: -1.0000
  参数数: 2

=== 风格 2: param_dict ===
  初始能量: 0.0994
  最终能量: -0.9974

=== 风格 3: 直接传入 tensor ===
  初始能量: 0.0974
  最终能量: -0.9977
```

**Figures**

![11 — 原生 Torch 训练（不依赖 TorchQuantum） — figure-01.svg](../_generated/examples/3_best_practices/figures/11_native_torch_training/figure-01.svg)

