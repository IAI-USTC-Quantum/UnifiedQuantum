# UnifiedQuantum 未解决问题清单

本文件记录本轮审计中**已识别但尚未修复**的问题。已修复内容见 `uniqc-report.md` / `skill-report.md` 中各 issue（绝大多数标记 [FIXED]）以及之后追加的 D1、D10 修复。

- 测试基线：`uniqc 0.0.11.dev10`，venv `.venv-test`（Python 3.12.13）
- 本表条目均**需要 API 设计决策、破坏性变更、或重型新功能**，因此未在前面的 surgical fix 阶段内完成
- 每条都附 ID（与 `uniqc-report.md` 对齐）、严重程度、根因、建议的修复方向

---

## 高优先级（影响真机使用 / 用户错误引导）

### D2 [bug · high] `submit_task` 错误提示与实际行为不符
- 文件：`uniqc/backend_adapter/task_manager.py`（错误信息构造处）
- 现象：当 `auto_compile` 校验失败时，错误信息建议用户 `auto_compile=False` 或设置 `UNIQC_SKIP_VALIDATION=true` 来绕过，但实际：
  1. `submit_task` 没有 `auto_compile=False` 这一参数
  2. `UNIQC_SKIP_VALIDATION` 必须在 **import uniqc 之前**设置才生效（D3 同因），运行期 `os.environ[...]=...` 无效
- 建议：
  - 删除"`auto_compile=False`"那行建议
  - 改为推荐 `submit_task(..., skip_validation=True)` 关键字（需新增），或改为提示用户在 shell 里 `export UNIQC_SKIP_VALIDATION=true` 并重启 Python
- 阻塞：需要决定 skip-validation 是改成运行期参数还是只保留环境变量

### D3 ~~[bug · medium] 环境变量在模块导入时一次性读取~~ ✅ 已修复
- **修复方案**：完全移除 `UNIQC_DUMMY` 环境变量和 `is_dummy_mode()` 函数。dummy 模式现在只通过 backend 名称前缀（`dummy`、`dummy:...`）激活，不再依赖环境变量。
- `UNIQC_SKIP_VALIDATION` 仍保留（待独立处理）。

### D4 [bug+doc · medium] `dummy:originq:<chip>` 隐式依赖 qiskit
- 现象：`find_backend("dummy:originq:WK_C180")` 在没有 qiskit extras 时报 ImportError，但 `dummy` 的卖点本应是"无 extras 即可本地仿真"
- 建议：把 dummy adapter 的电路转译路径从 qiskit-based 改为内置 OriginIR 解析；或把 qiskit 列入 `[dummy]` extras 必装；或在错误信息里清晰提示 `pip install uniqc[qiskit]`
- 阻塞：需决定是放进默认 install 还是另起 extras

### E2 [api · high] `ReadoutCalibrator.calibrate_1q/2q` 返回 dict
- 文件：`uniqc/calibration/readout.py`
- 现象：返回原始 dict（`{"qubit": 0, "confusion_matrix": [[..]], ...}`），但 `M3Mitigator` 等下游期望 `ReadoutCalibrationResult` dataclass
- 建议：返回 `ReadoutCalibrationResult`（与 D1 思路一致 —— 让 dataclass 同时实现 dict-like 协议以保持向后兼容）
- 阻塞：需要检查所有下游 `cal["confusion_matrix"]` 调用点；另需配合 E4 一并设计 1q/2q 自动校准统一接口

---

## 中优先级（API 一致性 / 性能）

### D5 [ux · medium] `compile_for_backend` 对云模拟器（无 topology）直接报错
- 现象：当目标后端是云模拟器（不暴露拓扑）时，调用 `compile_for_backend` 抛 NoTopologyError，而不是优雅降级到 unconstrained compile
- 建议：拓扑缺失时 fallback 到 `compile(circuit, level=2)`（不做布线），并发出 warning

### D6 [perf · medium] `RegionSelector.find_best_1D_chain` 大芯片无超时
- 现象：在 180-qubit 芯片上找 1D 链路会陷入指数搜索；测试中观察到 >2 分钟无返回
- 建议：加 `timeout` 参数（默认 30s），超时回退到贪心解；或改用 BFS + beam search

### D8 [api · medium] `list_backends()` 返回结构与名字直觉不符
- 现象：返回 `dict[platform, list[chip]]`，名字暗示 `list[backend_name]`
- 建议：rename 为 `list_backends_by_platform()`，新增真正返回 `list[str]`（如 `["originq:WK_C180", "quafu:ScQ-P18"]`）的 `list_backends()`
- 阻塞：破坏性 rename，需 deprecation 周期

### B2 [api · medium] `uniqc.get_backend` vs `uniqc.simulator.get_backend` 命名冲突
- 现象：两个不同语义的 `get_backend` 共存（一个找云后端，一个查找本地仿真器），import 顺序不同会得到不同函数
- 建议：simulator 那个改名 `make_simulator` / `get_simulator`，保留 `uniqc.get_backend` 为云后端入口

### A2 [doc · high] `Circuit.get_matrix()` 不存在
- 现象：`docs/guide/circuit.md` 整节"提取酉矩阵"承诺 `c.get_matrix()` 与 `NotMatrixableError`，二者均未实现
- 建议（二选一）：
  - 实现 `get_matrix()`（H/X/Y/Z/S/T/SX/RX/RY/RZ/CNOT/CZ/CPHASE/SWAP 至少覆盖）
  - 或把该节标注"Planned"并在 `__all__` 之外
- 当前 docs 修复仅做了"删除 xy 那行"等小改，本节未触碰

### C4 [api · low-med] `Circuit.measure(qubit_list, cbit_list)` 双 list 形式静默重复测量
- 现象：`c.measure([0,1,2], [0,1,2])` 会逐个把后续 cbit 覆盖到同一 qubit
- 建议：检查参数；要么显式不支持双 list 形式（改抛 ValueError），要么改成正确实现（zip 配对，已经隐含的就保持，只是修文档）

---

## 低优先级（清理 / 文档 / 弃用）

### E4 [inconsistency · medium] `ReadoutEM` 自动校准只覆盖 1q
- 现象：自动校准走 `calibrate_1q`，2q correlated readout 错误未自动校准
- 建议：自动校准时同时跑 `calibrate_2q` 收集相邻对，融合到 mitigation pipeline；或显式文档说明限制

### E6 [deprecation · low] 多处用 `datetime.utcnow()`
- 文件：calibration / qem / task_manager 中若干处
- 现象：Python 3.12 已弃用 `datetime.utcnow()`
- 建议：统一替换为 `datetime.now(datetime.UTC)`

### F4 [exceptions · low] 多个顶层导出的异常类没有 `raise` 点
- 文件：`uniqc/exceptions.py`
- 现象：`grep -r "raise XxxError"` 找不到部分异常类的实际 raise 位置
- 建议：要么删掉未使用的（破坏性导出变化），要么补 raise 路径，或加注释说明"仅供用户子类化"

### C5 [doc · low] `deutsch_jozsa_circuit` 已附带 MEASURE，文档未明示
- 建议：在文档算法章节里加一行 "Note: 已包含 MEASURE 指令，无需手动追加"

### D11 [observability · low] `audit_backends` quark 失败被静默
- 现象：quark 平台 fetch 失败时计入日志但不出现在最终 `issues` 列表里
- 建议：把 fetch 失败也作为 issue（severity=warning）输出

### F9 [config · low] `uniqc.config` 缺平台标准 key 名校验
- 现象：用户拼错 key（如 `originq.tokn`）时静默无效
- 建议：维护 schema，未知 key 触发 warning

---

## 验证盲区（环境受限，未能完整测试）

下列项需要在装齐 extras / 接入真机后再验证，本轮无法定结论：

- **真机 OriginQ 提交端到端**：需 `pip install pyqpanda3`。当前 `submit_task` 路径仅在 dummy 下走通；真机路径上的 `wait_for_result` → `UnifiedResult` 包装是否对所有 OriginQ 返回 schema 都能正确映射 counts，未验证。
- **Quafu / IBM / Quark 适配器全链路**：相关 cloud-integration 测试因缺 `quafu`/`qiskit`/`quarkstudio` 仍 10 个 fail，本轮均确认为预先存在、与本次修复无关。
- **TorchQuantum 后端**：未安装，相关 simulator 列表展示与 PyTorch 集成路径未活检。
- **MPS 大规模电路**：仅做了小规模冒烟，`chi_max=64` 默认在 100+ 量子比特下的实际行为没有 benchmark。

---

## 与已修复问题的对照

已在前几轮修复并验证（共 ~46 项），不在本表内：
- **代码层**：C1+C2、C3、E1+E5、E3、D7、D9、D10、F1、F5、A-bonus(`xy`)、**D1**
- **文档层**：A1/A3/A4/A5、B1/B5/B6/B7、F6/F7/F8
- **Skill 层**：A-S1..A-S5、B-S1..B-S2、C-S1..C-S3、D-S1..D-S9、E-S1..E-S7、F-S1..F-S7（共 35 项）

---

## 建议处理顺序

1. **D2 + D3** 一起做（错误信息 + 环境变量重读）—— 用户最容易踩
2. **D4** —— `dummy:` 是入门最常用路径，不应需要 qiskit
3. **E2 + E4** 一起做 —— readout 校准统一返回 dataclass 并支持 2q
4. **D8 / B2** —— 命名清理，破坏性，安排 deprecation
5. **A2** —— `get_matrix()` 实现或文档下线
6. 剩余低优先级清理项可批量处理
