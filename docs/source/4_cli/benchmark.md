# benchmark / noise / experiments

`uniqc benchmark`、`uniqc noise` 与 `uniqc experiments` 是本轮新增的三个命令组，
分别覆盖基准入口、噪声模型交换与实验覆盖清单。三者都只在本地执行，
不提交云任务、不消耗 shots 配额。

## uniqc benchmark

```bash
# 量子体积（Cross et al. 2019 判据；通过时 QV = 2^width）
uv run uniqc benchmark qv --width 4 --trials 20 --shots 1000 --seed 0 \
    --output qv-report.json

# 本地编译/执行吞吐（验收口径：平均每线路 1000 shots，>= 30,000 线路/小时）
uv run uniqc benchmark throughput --circuits 500 --qubits 8 --depth 6 \
    --shots 1000 --seed 0 --output throughput-report.json
```

要点：

- `qv` 的判据：单次 trial `h - 2σ > 2/3`，整体 `mean_h - 2σ_mean > 2/3`；
  未达标时命令退出码为 1。
- `throughput` 的计时边界是 OriginIR 解析/预处理 + 态矢量仿真 + shot 采样；
  进程启动、task store 持久化、报告 I/O 不计时。未达到 30,000/小时时退出码为 1。
- `--output` 写出的 JSON 报告包含完整输入集种子、计时与环境（CPU 后端、
  依赖来源、逻辑核数、测量时负载），可直接作为证据归档。
- `throughput --backend dummy:local:virtual-line-N` 等拓扑约束后端会把
  纠缠层限制在解析出的拓扑边内，编译路径照常执行拓扑校验。

## uniqc noise

```bash
# 校验并摘要一个 nlearn.noise-model.v1 交换文件
uv run uniqc noise import model.json --output summary.json

# 在导入的含噪 VM 上跑 3 层 QRAM 案例（读出缓解走统一 ReadoutEM 接口）
uv run uniqc noise qram model.json --case lookup --address 5 --shots 1000 --output case.json
uv run uniqc noise qram model.json --case qpu --shots 1000 --output case.json
```

能力边界：导入是离线数据交换（文件自带 SHA256 完整性校验），声明
`new_hardware_run: false`；本地案例使用密度矩阵含噪仿真，**不是**真机记录。
真实历史噪声数据由 noise-learning 产品导出为 `hardware_archive` /
`historical_replay` 交换文件后走同一入口。

## uniqc experiments

只读的实验覆盖清单：每个既有层析/标定/缓解实验的统一接口入口、离线本地验证
命令、冻结业务下的真机复测命令（**本轮不执行**）与历史记录来源。

```bash
uv run uniqc experiments list --category mitigation
uv run uniqc experiments show readout_em --json
```

清单同时登记：ZNE 历史未实现占位（与本轮业务冻结分开记录）、
134 个冻结业务源文件由 `scripts/check_engineering_freeze.py` 逐字节校验。

## 相关章节

- [基准测试](../2_advanced/benchmarks.md) —— 判据、计时边界与证据口径
- [版本化噪声模型交换](../2_advanced/noise_model_exchange.md) —— schema 与案例语义
- [Gateway Web UI](gateway.md) —— "Benchmarks" 页提供同样能力的图形入口
