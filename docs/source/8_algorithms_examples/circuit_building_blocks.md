# 线路构件

量子线路由基本构件（QFT、Oracle、纠缠态等）拼装而成。本节列出官方提供的
线路片段示例，它们都可以通过 ``Circuit.add_circuit()`` 自由组合。

## 示例

```{include} ../_generated/examples/2_advanced/circuits__qft.md
```

```{include} ../_generated/examples/2_advanced/circuits__grover_oracle.md
```

```{include} ../_generated/examples/2_advanced/circuits__deutsch-jozsa.md
```

```{include} ../_generated/examples/2_advanced/circuits__entangled_states.md
```

```{include} ../_generated/examples/2_advanced/circuits__dicke_state.md
```

```{include} ../_generated/examples/2_advanced/circuits__thermal_state.md
```

## 相关页面

- [构建量子线路](../1_basic_usage/circuit.md) —— `Circuit` 与 `add_circuit()` 的组合方式
- [Algorithm API 设计约定](../2_advanced/algorithm_design.md) —— 本页构件遵循的 `_circuit` 后缀等约定
- [态制备](state_preparation.md) 与 [核心量子算法](core_algorithms.md) —— 常用构件的下游用法
