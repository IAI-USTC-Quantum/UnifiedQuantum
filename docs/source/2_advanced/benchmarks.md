# 基准测试：量子体积与本地编译/执行吞吐

本页介绍 UniQC 的两个可复现基准入口，用于 NISQ 框架的软件能力验证。两者都在本地
模拟栈上真实执行，不提交云任务、不消耗 shots 配额。

```{note}
本页描述的是**软件入口与本地证据**。真机量子体积等指标需要另行授权的云端实验，
本地结果不能写成真机记录。
```

## 量子体积（Quantum Volume）

实现 Cross et al. (2019) 的模型线路与重输出判据：

- 宽度 `m`、深度 `m` 的模型线路：每层随机置换 + 相邻比特对上的 Haar 随机 SU(4)；
- SU(4) 用 CNOT 最优的两比特 Weyl 分解（3 CNOT + 8 个单比特旋转）打到 OriginIR 门集；
- 重输出 = 理想输出分布中概率严格大于中位数的基态；
- 单次 trial 通过条件 `h - 2σ > 2/3`，整体通过条件
  `mean_h - 2σ_mean > 2/3`，通过时该后端记 `QV = 2^m`。

所有随机性（模型线路、shot 采样）都来自显式种子，同一参数逐位可复现。

```bash
uv run uniqc benchmark qv --width 4 --trials 20 --shots 1000 --seed 0 --output qv-report.json
```

Python 入口：

```python
from uniqc.benchmark import run_quantum_volume

result = run_quantum_volume(width=4, trials=20, shots=1000, base_seed=0)
print(result.passed, result.quantum_volume, result.mean_h)
```

## 本地编译/执行吞吐

测量本地流水线在固定 shots/线路预算下的线路处理速率（验收口径：平均每线路
1000 shots，≥ 30,000 线路/小时）。

**计时边界（每线路）**：OriginIR 解析/预处理（编译）+ 态矢量仿真 + shot 采样（执行）。
进程启动、任务持久化（SQLite task store）、报告序列化与文件 I/O 明确排除在计时外。

```bash
uv run uniqc benchmark throughput --circuits 500 --qubits 8 --depth 6 --shots 1000 --output throughput-report.json
```

报告 JSON 记录：输入集生成器与种子、拓扑匹配模式、编译/执行分项计时、
每小时的线路数、是否达到 30,000/h、CPU 后端与依赖来源（PyPI
`uniqc-cppsimulator>=1.0.1,<2`）、Python/NumPy 版本、逻辑核数与测量时负载。

拓扑约束后端（如 `dummy:local:virtual-line-N`、`virtual-grid-RxC`）会自动把
纠缠层切换为基于解析拓扑边的随机匹配，编译路径照常执行拓扑校验。

## 实验覆盖清单

`uniqc experiments` 提供只读的实验覆盖清单：每个既有层析/标定/缓解实验的统一接口
入口、离线本地验证命令、冻结的真机复测命令（本轮**不执行**）与历史记录来源。

```bash
uv run uniqc experiments list
uv run uniqc experiments show readout_em --json
```

相关内容也可参见 {doc}`noise_model_exchange` 与 {doc}/3_best_practices/index.md。
