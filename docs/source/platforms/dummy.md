(platforms-dummy)=
# Dummy 本地模拟

## 简介

`dummy` 是 uniqc 内置的本地模拟器后端，**无需安装 extra、无需凭证、无需
网络**。它既可以做无噪声的快速验证，也可以复用真实芯片的拓扑与标定数据
做本地含噪模拟。

## 安装与配置

默认安装即可，无需任何配置。

## 查看后端

```bash
uniqc backend list -p dummy
```

## Backend 编号规则

| backend id | 语义 |
|------------|------|
| `dummy` | 无约束、无噪声虚拟机（`dummy:local:simulator` 的简写） |
| `dummy:local:simulator` | 无约束、无噪声本地模拟 |
| `dummy:local:virtual-line-N` | N 比特线性拓扑，无噪声 |
| `dummy:local:virtual-grid-RxC` | R×C 比特网格拓扑，无噪声 |
| `dummy:virtual:<name>` | 使用 `~/.uniqc/backend/virtual/<name>.yaml` 中的自定义拓扑与噪声模型 |
| `dummy:<platform>:<chip>` | 复用真实 backend 的拓扑与标定数据，先 compile/transpile，再本地含噪执行 |

`dummy:<platform>:<chip>` 是规则型写法，不需要提前注册；运行时会解析真实
backend 的 topology / chip characterization，自动注入去极化噪声与读出误差
（缺标定数据时使用默认值）。

## 提交任务

```bash
# 无约束、无噪声（默认 backend 即 dummy:local:simulator）
uniqc submit circuit.ir --backend dummy --shots 1000 --wait

# 虚拟线性拓扑
uniqc submit circuit.ir --backend dummy:local:virtual-line-3 --shots 1000 --wait

# 针对真实芯片的本地含噪仿真
uniqc submit circuit.ir --backend dummy:originq:WK_C180 --shots 1000 --wait
uniqc submit circuit.ir --backend dummy:tianyan:tianyan176 --shots 1000 --wait
uniqc submit circuit.ir --backend dummy:logicalqubit:<chip> --shots 1000 --wait
```

Python：

```python
from uniqc import Circuit, submit_task, wait_for_result

c = Circuit()
c.h(0)
c.cnot(0, 1)
c.measure(0)
c.measure(1)

task_id = submit_task(c, backend="dummy:local:simulator", shots=1000)
print(wait_for_result(task_id))
```

## 平台约定与限制

- 提交为**同步**：本地立即执行，结果立即可用。
- 虚拟拓扑后端只施加拓扑约束，不注入噪声；含噪模拟请用
  `dummy:<platform>:<chip>` 或 `dummy:virtual:<name>`。
- 标定数据如何转换为噪声参数等细节见
  {ref}`平台约定的 DummyBackend 一节 <platform-dummy-backend>`。

## 相关页面

- [本地模拟](../1_basic_usage/simulation.md) —— 直接使用 Python 模拟器类（不经任务流水线）
- [自定义含噪量子虚拟机](../2_advanced/virtual_backends.md) —— `dummy:virtual:<name>` 的 YAML 配置详解
- [噪声模拟](../2_advanced/noise_simulation.md) —— 含噪后端的错误模型与读出误差机制
- [MPS 模拟器](../2_advanced/mps_simulator.md) —— `dummy:local:mps-linear-N` 后端背后的引擎
- [动态电路](../2_advanced/dynamic_circuits.md) —— `dummy:local:simulator` 支持的经典控制流
- [CLI backend 命令](../4_cli/backend.md) —— 虚拟机的创建 / 校验 / 列举子命令
