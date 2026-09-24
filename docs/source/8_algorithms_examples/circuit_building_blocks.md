# 线路构件

量子线路由基本构件（{py:func}`QFT <uniqc.algorithms.core.circuits.qft.qft_circuit>`、
{py:func}`Oracle <uniqc.algorithms.core.circuits.grover_oracle.grover_oracle>`、
{py:mod}`纠缠态 <uniqc.algorithms.core.circuits.entangled_states>` 等）拼装而成。本节列出官方提供的
线路片段示例，它们都可以通过 {py:meth}`Circuit.add_circuit() <uniqc.circuit_builder.qcircuit.Circuit.add_circuit>` 自由组合。

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
