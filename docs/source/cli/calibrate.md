# 校准命令 (`uniqc calibrate`)

`uniqc calibrate` 用于生成后续 QEM 和噪声建模需要的实验数据。校准模块只负责运行实验并写入 `~/.uniqc/calibration_cache/`；QEM 模块在读取这些数据时检查 `calibrated_at` 和 TTL。

## 子命令

| 子命令 | 说明 |
|--------|------|
| `xeb` | 运行 1q / 2q XEB，估计每层门保真度 |
| `readout` | 运行 1q / 2q 读出校准，生成 confusion matrix |
| `pattern` | 分析并行 2q gate 执行分组 |

## XEB

```bash
# 本地快速验证
uniqc calibrate xeb --backend dummy --type 1q --qubits 0 1 --depths 5 10

# 更完整的本地基准
uniqc calibrate xeb --backend dummy --type both --qubits 0 1 2 3 \
    --depths 5 10 20 50 --n-circuits 50 --shots 1000

# 写出 JSON 结果
uniqc calibrate xeb --backend dummy --type 1q --qubits 0 1 \
    --output xeb_results.json
```

常用选项：

| 选项 | 说明 |
|------|------|
| `--backend`, `-b` | 后端名称；`dummy` 使用本地模拟，OriginQ 可使用 `WK_C180` 等后端名 |
| `--type` | `1q`、`2q` 或 `both` |
| `--qubits`, `-q` | 参与基准测试的量子比特 |
| `--depths`, `-d` | 随机线路深度列表 |
| `--n-circuits` | 每个深度生成的随机线路数量 |
| `--no-readout-em` | 跳过读出误差缓解，输出原始 XEB 估计 |
| `--seed` | 固定随机线路生成 |

## Readout

```bash
# 生成本地读出校准数据
uniqc calibrate readout --backend dummy --qubits 0 1 --shots 1000

# 只做 1q 读出校准
uniqc calibrate readout --backend dummy --type 1q --qubits 0 1 2

# 写出 JSON 结果
uniqc calibrate readout --backend dummy --qubits 0 1 --output readout.json
```

读出校准结果会保存 assignment fidelity 和 confusion matrix。后续 `uniqc.qem` 会按 `calibrated_at` 检查数据是否过期。

## Pattern

```bash
# 根据线性拓扑生成并行 2q 分组
uniqc calibrate pattern --qubits 0 1 2 3 --type auto

# 从 OriginIR 文件中抽取并行 2q 分组
uniqc calibrate pattern --type circuit --circuit circuit.ir
```

`pattern` 主要用于并行 XEB 和芯片调度检查。输出包含 `n_rounds`、`chromatic_number` 和每轮可并行执行的 2q gate 分组。
