# 线路分析

(advanced-circuit-analysis)=

## 什么时候进入本页

当你需要查看线路信息（深度、门统计）、绘制线路图、分析门类型与数量，或了解量子比特重映射时，进入本页。

本页是 [构建量子线路](../1_basic_usage/circuit.md) 的延伸阅读，适合已经完成线路构建、需要进一步分析或可视化线路结构的读者。

> 如果你还未完成基础线路构建，建议先阅读 [构建量子线路](../1_basic_usage/circuit.md)。

## 线路信息

```python
circuit.depth          # 线路深度
circuit.qubit_num      # 量子比特数
circuit.cbit_num       # 经典比特数
circuit.opcode_list    # 门操作列表
```

## 量子比特重映射

```python
# 将线路中的量子比特索引重新映射
remapped = circuit.remapping({0: 3, 1: 5})
```

> 注意：当前 `remapping` 不支持部分重映射。

## 可视化

```python
# 终端：字符画（自研，无第三方依赖；Python 3.14 可用）
print(circuit.draw("text"))

# Jupyter / 文档：矢量图（风格可选 quantikz/qiskit/modern/print）
circuit.draw("svg", style="quantikz", filename="circuit.svg")

# 论文：quantikz LaTeX 源码
print(circuit.draw("latex"))
```

七种模式：``text``（字符画）、``svg``、``png``、``mpl``（matplotlib Figure）、
``latex``（quantikz 源码）、``html``（静态）、``interactive``（点击门看详情）。
统一选项：``style`` / ``fold``（每行门数）/ ``orientation`` / ``qubit_order`` /
``theme`` / ``param_mode`` / ``show_clbits`` / ``filename``，详见
{py:func}`uniqc.visualization.render <uniqc.visualization.circuit_render.render>`。覆盖 OriginIR-ext 全特性（含误差通道、QRAM、
经典控制流）。

> 时序（timeline）可视化见 `uniqc.visualization.schedule_circuit` 与
> `plot_time_line`；结果分布见 `plot_histogram` / `plot_distribution`。

## 线路转译

UnifiedQuantum 支持 OriginIR 和 QASM 格式互转。

```python
# Circuit 同时支持两种格式输出
originir_str = circuit.originir
qasm_str = circuit.qasm
```

> 详细的门对照表见 [QASM 2.0 文档](../1_basic_usage/qasm.md)；`Circuit` 侧的格式转换入口见
> [格式转换](guide-circuit-format-conversion)。

## 相关页面

- [构建量子线路](../1_basic_usage/circuit.md) —— `Circuit` 构建全景（本页是其延伸）
- [编译选项与 Region 选择器](compiler_options_region.md) —— 编译到具体芯片拓扑与基门集
- [编译策略](advanced-compile-levels) —— 提交时的 `local_compile` / `cloud_compile` 等级
- [算法实现示例](../8_algorithms_examples/index.md) —— 各算法线路的深度/门统计实例
- [CLI 线路绘制](../4_cli/draw.md) —— 命令行渲染线路图
