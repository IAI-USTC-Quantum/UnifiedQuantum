# 主路径走读 (Walkthrough)

把 **构造电路 → 本地模拟 → 提交并后处理 → 配置 → 可视化** 五件事按顺序串一遍。
每一节都来自 ``examples/1_basic_usage/0X_*.py``，由文档构建器自动重跑、把输出拼进文档，
所以只要本地能 `make html`，这些示例就一定是可运行的。

(circuit-basics)=
## 1. 构造电路：原生 Circuit、qreg、OriginIR / QASM 导出

```{include} ../_generated/examples/1_basic_usage/01_circuit_basics.md
```

更深入的电路构建（控制结构、参数化、Named Circuit、酉矩阵提取等）见
[构造电路](circuit.md)。

(local-simulation)=
## 2. 本地模拟

```{include} ../_generated/examples/1_basic_usage/02_local_simulation.md
```

不同 backend 的语义差异、噪声后端选择见 [本地模拟](simulation.md)。

(submit-postprocess)=
## 3. 通过 ``submit_task`` 提交并后处理

```{include} ../_generated/examples/1_basic_usage/03_submit_and_postprocess.md
```

各平台特有 kwarg、批量提交、错误处理见 [提交任务](submit_task.md) 与
[任务管理器](task_manager.md)。

(config)=
## 4. 配置文件 / `~/.uniqc/config.yaml`

UnifiedQuantum 把 token、proxy、profile 等配置统一存放在 ``~/.uniqc/config.yaml``，
并通过 ``UNIQC_PROFILE`` 环境变量切换 profile。

```{include} ../_generated/examples/1_basic_usage/04_config.md
```

各平台的配置约定与 chip-id 命名见 [平台约定](platform_conventions.md)。

(visualize)=
## 5. 可视化

```{include} ../_generated/examples/1_basic_usage/05_visualize.md
```

## 真机提交模板

```python
from uniqc import Circuit, dry_run_task, submit_task, wait_for_result

c = Circuit(); c.h(0); c.cnot(0, 1); c.measure(0, 1)

# 1. 离线检查（推荐每次都先 dry_run）
print(dry_run_task(c, backend="originq", backend_name="WK_C180", shots=1000))

# 2. 真机提交
task_id = submit_task(c, backend="originq", backend_name="WK_C180", shots=1000)
print(wait_for_result(task_id))
```

更多真机相关的细节（``dummy:<platform>:<backend>``、calibration cache、QEM）在
[进阶教程](../2_advanced/index.md)。
