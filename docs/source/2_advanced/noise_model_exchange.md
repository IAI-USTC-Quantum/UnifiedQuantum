# 版本化噪声模型交换与含噪 VM

UniQC 以**数据文件**方式消费噪声学习（noise-learning）产品导出的版本化噪声模型，
不 import 私有 `nlearn` 包——交换文件自包含全部通道信息，并以规范 SHA256 校验完整性。

## 交换文件（`nlearn.noise-model.v1`）

生产端（noise-learning）把学习到的通道序列化为 JSON：

- `schema: nlearn.noise-model.v1`、`data_class`（`synthetic` / `hardware_archive` /
  `historical_replay`）、`new_hardware_run: false`（离线交换，不是新真机运行）；
- 布局与拓扑：物理链 `layout.physical_chain`、局部边 `topology.local_edges`；
- 通道：逐比特 Pauli-1q（RPhi 脉冲）、逐边 Pauli-2q（CZ）、逐比特读出
  `p01/p10`、可选的测后边缘翻转混合；
- 消费者绑定 `uniqc.noisy_simulator.v1`：密度矩阵模拟器 + 逐门实例 Pauli 通道 +
  读出误差 + 虚拟 RZ 免噪。

## 导入与执行

```python
from uniqc.noise_bridge import load_noise_model

model = load_noise_model("model.json")       # 校验 schema + SHA256
sim = model.to_simulator()                   # NoisySimulator(密度矩阵后端)
adapter = model.to_adapter()                 # DummyAdapter，走统一 submit/query 流程
counts = model.simulate_counts(circuit, shots=1000, seed=0)
```

命令行：

```bash
uv run uniqc noise import model.json --output summary.json
uv run uniqc noise qram model.json --case lookup --address 5 --shots 1000 --output case.json
```

## 含噪 VM 的 3 层 QRAM / QPU 寻址 / 缓解

`uniqc.noise_bridge.qram_cases` 提供两个固定输入的功能案例（线路只使用
RPhi/CZ 原生门以真实经过学习通道；QRAM 调用本身按模型定义免噪）：

- **3 层 QRAM 基址查找**：3 位地址（8 条数据）查询 `QRAMDECL` 内存，
  报告原始/缓解后准确率与计数；
- **QPU 超位寻址**：地址寄存器制备为纠缠叠加态后查询，数据寄存器分布
  反映量子寻址的内存内容，报告与理想分布的经典保真度；
- **读出缓解**：噪声计数经统一 `ReadoutEM` 接口缓解，校准电路跑在同一
  含噪 VM adapter 上。

```python
from uniqc.noise_bridge import run_qpu_addressing_case, run_qram_lookup_case

lookup = run_qram_lookup_case(model, address=5, shots=1000, seed=0)
qpu = run_qpu_addressing_case(model, shots=1000, seed=0)
```

## 能力边界

- 本页全部为**本地仿真**能力：合成模型 (`data_class: synthetic`) 的量级贴近
  WK_C180，但不是硬件测量，不得写成真机证据；
- 真实历史噪声数据以 `hardware_archive` / `historical_replay` 交换文件交付，
  走同一导入路径，导入动作本身离线、不产生新真机运行；
- 硬件 QRAM 访问实验需用户自行配置后端并运行；本页展示的离线导入与本地仿真
  不会发起设备任务，也不作为硬件验证结果。
