# UnifiedQuantum 代码/文档不匹配报告

- 测试版本：`uniqc 0.0.11.dev10`
- 环境：`/home/agony/projects/quantum-simulator-paper-new/.venv-test`（Python 3.12.13），未安装 `qiskit / pyqpanda3 / quafu / quarkstudio / torch / torchquantum / qutip` extras
- 真机 API key：OriginQ key 已在 `~/.uniqc/config.yaml`，但实际云提交受 `pyqpanda3` extras 缺失阻塞，未做端到端真机提交
- 审计分 6 域并行执行，本报告仅汇总「代码错误 / 文档错误 / 文档缺失」类问题；skill 类问题见 `skill-report.md`

---

## A. circuit / compile / visualization

### A1 [doc · medium] `Circuit.xy(...)` 不存在但文档列出
- 文件：`UnifiedQuantum/docs/source/guide/circuit.md:58`
- 现象：文档把 `xy` 列入双量子比特门便捷方法 (`xx, yy, zz, xy, phase2q, uu15`)，实际 `Circuit` 没有 `xy` 方法。`XY` 在 `available_originir_gates` 中存在，需要 `c.add_gate('XY', [0,1], None, [theta])` 手动调用。
  ```python
  Circuit().xy(0,1,0.3)   # AttributeError: 'Circuit' object has no attribute 'xy'
  ```
- 建议：给 `Circuit` 加 `xy(q1,q2,theta)` 便捷方法（与 xx/yy/zz 同款），或把 `circuit.md:58` 中的 `xy` 删掉。

### A2 [doc · high] `Circuit.get_matrix()` 不存在
- 文件：`UnifiedQuantum/docs/source/guide/circuit.md:139-154`（整节「提取酉矩阵」）
- 现象：`dir(Circuit)` 中无任何 `matrix`/`unitary` 方法；文档承诺的 `NotMatrixableError` 异常类同样不存在。
  ```python
  c = Circuit(); c.h(0); c.cnot(0,1)
  matrix = c.get_matrix()   # AttributeError
  ```
- 建议：实现 `get_matrix()`（覆盖文档列出的 H/X/Y/Z/S/T/SX/RX/RY/RZ/CNOT/CZ/CPHASE/SWAP），或将整节「提取酉矩阵」删除/标注「计划中」。

### A3 [doc · low] `Parameter.evaluate(values=...)` 行为与文档相反
- 文件：`UnifiedQuantum/docs/source/guide/circuit.md:217-226`
- 现象：文档示例
  ```python
  theta.bind(1.0)
  result = theta.evaluate({"theta": 2.0})  # 文档承诺返回 2.0
  ```
  实际返回 `1.0`（bound 值优先于 dict）。docstring 也确认 “If the parameter is bound, returns the bound value”。
- 建议：把示例改成「先 unbind 再 evaluate(dict)」，或注明 `bound` 状态下 dict 被忽略。

### A4 [doc · high] `compile()` 不接受 `config=` 关键字参数
- 文件：`UnifiedQuantum/docs/source/guide/compiler_options_region.md:78-82`
- 现象：
  ```python
  compile(circuit, config=TranspilerConfig(level=2))
  # TypeError: compile() got an unexpected keyword argument 'config'
  ```
  实际签名 `compile(circuit, backend_info=None, *, type='qiskit', level=2, basis_gates=None, chip_characterization=None, output_format='circuit') -> Circuit | str`。返回值是 `Circuit | str`，**不是 `CompilationResult`**（后者仅由内部未导出的 `compile_full()` 返回）。
- 建议：① 把示例改成 `compile(circuit, backend_info, level=3, basis_gates=[...], chip_characterization=chip)`；② 文档明确 `compile()` 直接返回 `Circuit/str`；③ 若希望保留「类型化 config」入口，考虑添加 `config=` 关键字或 export `compile_full`。

### A5 [doc · medium] `schedule_circuit` / `plot_time_line*` 即使提供 `gate_durations` 仍要求 qiskit
- 文件：`UnifiedQuantum/uniqc/visualization/timeline.py:170-184`；docs 未提及该依赖
- 现象：
  ```python
  schedule_circuit(c, gate_durations={'H':30,'CNOT':200,'MEASURE':1000})
  # CompilationFailedException: compile() requires the optional qiskit dependencies
  ```
  对所有「无 explicit start」的逻辑线路，函数都会无条件调用 `compile()` 进基门展开，因此即便 `gate_durations` 已提供也强制需要 qiskit；错误信息仍指向 `compile()`，对调用方可视化函数的用户造成误导。
- 建议：文档明确「逻辑线路 → timeline 需要 `unified-quantum[qiskit]`」；或在 `gate_durations` 已覆盖所有出现的门时跳过基门展开。

---

## B. simulators

### B1 [bug · medium] `OriginIR_NoisySimulator` 默认 backend 与噪声路径不兼容
- 文件：`UnifiedQuantum/uniqc/simulator/originir_simulator.py:108`、`UnifiedQuantum/docs/source/guide/simulation.md:118-126`
- 现象：`OriginIR_NoisySimulator.__init__` 默认 `backend_type='statevector'`，且 `simulation.md` 噪声示例正是用默认值构造，但 `sim.simulate_pmeasure(...)` 立刻抛 `ValueError: simulate_pmeasure is only available for density_operator type OpcodeSimulator backend`。`noise_simulation.md` 反过来要求「必须使用 density_matrix 后端」——两份文档相互打架，且默认值本身跑不通。
- 建议：把默认 `backend_type` 改成 `'density_matrix'`（或在 statevector + 非空 noise 时直接报错），并修正 `simulation.md` 示例与 `noise_simulation.md` 对齐。

### B2 [api · medium] `uniqc.get_backend` vs `uniqc.simulator.get_backend` 命名冲突
- 文件：`UnifiedQuantum/uniqc/simulator/get_backend.py:62`、`UnifiedQuantum/uniqc/backend_adapter/backend.py:748`、`UnifiedQuantum/uniqc/__init__.py`
- 现象：顶级 `uniqc.get_backend` 来自 `backend_adapter.backend`（签名 `(backend_id, *, config=...)` 用于云/dummy 解析）；`uniqc.simulator.get_backend` 是本地模拟器工厂（签名 `(program_type='originir', backend_type='statevector', **kw)`）。两者**不是同一对象**且签名不兼容，但同名、同 namespace 邻近，极易混淆。
- 建议：把 `simulator/get_backend.py` 的 `get_backend` 重命名为 `get_simulator`（或仅保留 `create_simulator`），不再 re-export 旧名；如保留兼容请在 docstring 明确区别。

### B3 [api · low] `create_simulator` 接受的别名比 `OriginIR_Simulator` 多
- 文件：`UnifiedQuantum/uniqc/simulator/get_backend.py:43`、`UnifiedQuantum/uniqc/simulator/opcode_simulator.py:13`
- 现象：`create_simulator(backend='density')` 工作并返回 `OriginIR_Simulator(backend_type='densitymatrix')`；但用户直接 `OriginIR_Simulator(backend_type='density')` 抛 `ValueError: Unknown backend type: density`。两个入口的 alias 集合不一致。
- 建议：`backend_alias` 增加 `'density'`，让两套入口语义统一；或反向收紧 `create_simulator` 的别名集合。

### B4 [error msg · low] `density_matrix_qutip` 缺包时报错信息丢失
- 文件：`UnifiedQuantum/uniqc/simulator/opcode_simulator.py:65-72`
- 现象：qutip 未装时，`OpcodeSimulator(backend_type='density_matrix_qutip')` 真正的异常是 `ModuleNotFoundError: No module named 'qutip'`，未被 `try/except ImportError` 包成「install unified-quantum[simulation]」的友好提示（实测异常向上冒泡时显示原生信息）。
- 建议：`from .qutip_sim_impl import ...` 的 `try/except` 也覆盖 `ModuleNotFoundError`，或在外层再 wrap 一次。

### B5 [doc · medium] `mps_simulator.md` `chi_max` 默认值写错
- 文件：`UnifiedQuantum/docs/source/advanced/mps_simulator.md:53`
- 现象：文档写 `chi_max: int = 256`，但 `uniqc/simulator/mps_simulator.py:71` 实际默认 `64`（`dummy:mps` 路径同样 64）。会让用户误以为 `MPSConfig()` 自带 256 的键维上限，从而低估截断风险。
- 建议：把默认值改为 64，并补充内存量级说明。

### B6 [doc · low] `simulation.md` 后端列表遗漏 MPS / TorchQuantum
- 文件：`UnifiedQuantum/docs/source/guide/simulation.md:43-50, 150-157`
- 现象：本地模拟入口表只列 `OriginIR_Simulator / QASM_Simulator / OpcodeSimulator / OriginIR_NoisySimulator`，API 参考也只列前三个；但 `uniqc.simulator` 已正式 re-export `MPSSimulator / MPSConfig / TorchQuantumSimulator`，`create_simulator` 同时支持 `mps / torchquantum`。
- 建议：在「本地模拟入口总览」与「API 参考」追加 MPSSimulator、TorchQuantumSimulator（标注 extras 依赖），并 cross-link 到 `advanced/mps_simulator.md` 与 pytorch 指南。

### B7 [doc · low] `noise_simulation.md` 示例缺 import
- 文件：`UnifiedQuantum/docs/source/advanced/noise_simulation.md:15-38, 58-65`
- 现象：快速开始片段调用 `ErrorLoader_GenericError(...)` 但只 `from uniqc.simulator.error_model import Depolarizing`；「使用示例」片段调用 `TwoQubitDepolarizing(0.005)` 但只 import 了 `BitFlip, Depolarizing`。原样复制粘贴均 NameError。
- 建议：补全 import 行，与「完整示例」一节保持一致。

---

## C. algorithms + expectation

### C1 [bug · high] `dicke_state_circuit(k=1, ...)` 退化为单一基态
- 文件：`UnifiedQuantum/uniqc/algorithms/core/circuits/dicke.py`
- 现象：3 qubits, `k=1` 只输出 `|100⟩`，不是 `(|001⟩+|010⟩+|100⟩)/√3`：
  ```python
  c = Circuit(); dicke_state_circuit(c, k=1, qubits=[0,1,2]); c.measure(0,1,2)
  print(OriginIR_Simulator().simulate_shots(c.originir, 4096))
  # {4: 4096}   ← 应为 {1, 2, 4} 大致均分
  ```
  k=2、k=3 正确；只有 k=1 错。`uniqc.state_preparation.dicke_state`（无 `_circuit` 后缀）实现正确，可作对照。
- 建议：修复 `dicke_state_circuit` 的 split-and-spread（首层 `X q[2]` 之后缺少把激发扩散到其他 qubit 的步骤），或在 `__init__` 中将其重定向到 `dicke_state`。

### C2 [bug · high] `w_state` 退化为单一基态 `|100⟩`
- 文件：`UnifiedQuantum/uniqc/algorithms/core/state_preparation/w_state.py`
- 现象：3 qubits 输出 `|100⟩`，不是 W 态。
  ```python
  c = Circuit(); w_state(c, qubits=[0,1,2]); c.measure(0,1,2)
  # {4: 4096}
  ```
- 建议：与 `dicke_state(k=1)` 一致实现；或直接在 `w_state` 内部调用 `dicke_state(..., k=1)`。

### C3 [bug · medium] `state_tomography` 在没有 qutip 时崩溃
- 文件：`UnifiedQuantum/uniqc/algorithms/core/measurement/state_tomography.py:463,492`
- 现象：缺 qutip 时 fallback：
  ```
  rho = np.zeros((d, d), dtype=float)        # L463
  rho[a, b] = val / (2**n)                   # L492，val 是 complex
  TypeError: float() argument must be a string or a real number, not 'complex'
  ```
- 建议：fallback `rho` 初始化改成 `dtype=complex`，最终 `.real` 取实部即可（其实下方代码已经这样做）。

### C4 [api · low-med] `Circuit.measure(qubit_list, cbit_list)` 双 list 调用形式静默重复测量
- 文件：`uniqc.circuit_builder.qcircuit.Circuit.measure`
- 现象：签名是 `measure(*qubits)`，但 "qubit list + cbit list" 风格调用，两个 list 都被当 qubit，结果 2N 条 MEASURE 指令，引发 simulator 报 `Exceed total (total_qubit=N, measure_list size=2N)`：
  ```python
  c = Circuit(); c.h(0); c.h(1); c.measure([0,1], [0,1])   # 4 条 MEASURE，CREG=4
  ```
- 建议：(1) 在 `measure` 中检测「参数全为 list」并报错；(2) simulator 对相同 qubit 的重复 MEASURE 应允许（仅写到不同 cbit）。

### C5 [doc · low] `deutsch_jozsa_circuit` 已附带 MEASURE，文档需明示
- 文件：`uniqc/algorithms/core/circuits/deutsch_jozsa.py`
- 现象：调用 `deutsch_jozsa_circuit(c, oracle, qubits, ancilla)` 后 IR 末尾已含 `MEASURE`。若用户按惯例再 `c.measure(...)`，叠加 C4 直接报错。
- 建议：docstring/best-practice 明确「本函数已包含测量；请勿再附加 `circuit.measure(...)`」。

### 备注（无 bug）
- `calculate_expectation` **只支持 `Z`/`I` Hamiltonian**，不接受 `"Z0 Z1"` 形式（与 `qaoa_ansatz / pauli_expectation` 的 Pauli string 不同）。源码 docstring 已说明，但易引起跨 API 误用。建议在文档中加一行交叉提示。
- `calculate_multi_basis_expectation` basis label 仅取首字符决定 X/Y/Z，且只针对单个 qubit；要算 `⟨X⊗X⟩` 必须用 `pauli_expectation`。源码 docstring 已说明。

---

## D. backend adapter + cloud

### D1 [api · high] `wait_for_result` 返回类型与 `UnifiedResult` 不一致
- 文件：`uniqc/backend_adapter/task_manager.py`
- 现象：`wait_for_result(task_id, ...)` dummy 与 originq 路径都返回 `dict`（dummy 是 `{bitstring: int}`，无 `counts/probabilities/shots/platform/task_id`）。`UnifiedResult` 在顶层导出却完全不被该入口使用，仅在 `normalize_*` 工具内部返回。
- 建议：让 `wait_for_result` 返回 `UnifiedResult`（推荐，与公开类一致）；或把 `UnifiedResult` 标记为 internal 并删 re-export；至少把当前 dict shape 写进 docstring/类型 hint。

### D2 [bug · high] `submit_task` 错误提示与实际行为不符
- 文件：`uniqc/backend_adapter/task_manager.py::_prepare_circuit_for_submission` (~L562)
- 现象：对 `originq:full_amplitude` 提交 H/CNOT 线路：
  ```
  UnsupportedGateError: Circuit uses gates outside the backend basis set: ['CNOT','H'].
  Allowed: ['CZ','RZ','SX']. Pass auto_compile=False to bypass, or set UNIQC_SKIP_VALIDATION=true.
  ```
  传 `auto_compile=False` 抛同样错误；`auto_compile=True` 不会自动编译；唯一可绕过的是 `UNIQC_SKIP_VALIDATION=true` 环境变量（且必须在 import 之前设）。
- 建议：(a) 让 `auto_compile=True` 真的调用 compiler；(b) `auto_compile=False` 真的跳过 validation；(c) 错误文案别再推荐两个不工作的开关。

### D3 ~~[bug · medium] `UNIQC_DUMMY` 在模块导入时一次性读取~~ ✅ 已修复
- **修复方案**：完全移除 `UNIQC_DUMMY` 环境变量、`is_dummy_mode()` 函数及 `dummy=` 参数。dummy 模式现在只通过 backend 名称前缀（`dummy`、`dummy:...`）激活。

### D4 [bug+doc · medium] `dummy:originq:<chip>` 隐式依赖 qiskit
- 现象：`submit_task(c, backend='dummy:originq:WK_C180', ...)` 走 `_compile_for_chip_backed_dummy → compile()`，强依赖 qiskit transpiler；本环境无 qiskit 时直接 `CompilationFailedException`。同时 `find_backend('dummy:originq:WK_C180')` 抛 `ValueError`，与「这是提交规则而非 list 项」的设计自洽，但用户难以发现。
- 建议：在 `dummy:<platform>:<chip>` 文档与错误消息里明确列出 transpiler extras 要求；或退化为 OriginIR-level 的轻量 transpile（不依赖 qiskit）。

### D5 [ux · medium] `compile_for_backend` 对云模拟器（无 topology）直接报错
- 现象：`originq:full_amplitude` 是 simulator，`topology=()`、`extra` 无 connectivity；`compile_for_backend` 抛 `ValueError: compile() requires either backend_info.topology or chip_characterization.connectivity`。
- 建议：simulator backend 应跳过 routing，只做基组合成；或在异常中明确「simulator 不需要 compile，可直接 submit」。

### D6 [perf · medium] `RegionSelector.find_best_1D_chain` 在大芯片上无超时退出
- 文件：`uniqc/backend_adapter/region_selector.py::find_best_1D_chain`
- 现象：`find_best_1D_chain(length=3, start=10)` 在 169-qubit `WK_C180` 上 30 s 仍未返回；`find_best_2D_from_circuit` 有 `max_search_seconds`，1D 版本没有。
- 建议：加 `max_search_seconds` / 启发式剪枝，并暴露进度回调。

### D7 [bug · low] `RegionSelector.get_edge_rankings` 出现自环 `(0,0)`
- 现象：`WK_C180.get_edge_rankings()` 第一项是 `((0, 0), 0.9999)` —— 不是合法的两比特边。
- 建议：构图时跳过 `u==v`。

### D8 [api · medium] `list_backends()` 返回结构与名字直觉不符
- 现象：返回的不是 `dict[platform, list[BackendInfo]]`，而是 `{platform: {'platform': ..., 'available': ..., 'class': ...}}` 这种 metadata；要拿真实 backend list 必须用 `fetch_all_backends()` / `fetch_platform_backends(...)`。这与 CLI 的 `uniqc backend list` 行为对不上。
- 建议：要么改名为 `list_platforms`，要么真正返回 backend 列表。

### D9 [api · low] `BackendOptionsFactory.from_kwargs` 签名反直觉
- 现象：`from_kwargs(platform, kwargs)` 接受**位置 dict**，而非 `**kwargs`，调用 `f.from_kwargs('quafu', shots=100)` 直接 `TypeError`。
- 建议：改成真正的 `**kwargs`，或重命名 `from_dict`。

### D10 [stale default · low] `OriginQOptions.backend_name` 默认 `'origin:wuyuan:d5'`
- 现象：默认指向疑似已弃用的 `origin:wuyuan:d5`，与现网 backend list（`WK_C180 / PQPUMESH8 / HanYuan_01 / full_amplitude` 等）无对应。
- 建议：默认改为 `None`（要求显式指定）或 `'full_amplitude'`（cloud sim）。

### D11 [observability · low] `audit_backends` 在 quark 平台报告 fetch 失败但不计入 issues
- 现象：缺失 extras 的平台被静默跳过（仅 stderr 日志 `Skipping quark: ...`）。
- 建议：把「平台 fetch 失败」作为一条 `BackendAuditIssue(severity='warning', field='platform')`，便于程序化检测。

### 验证盲区（环境受限）
- 真实云端 `submit/wait_for_result` round-trip 未被覆盖，因 `unified-quantum[originq]` (`pyqpanda3`) 未装；建议补一个不依赖 `pyqpanda3`、走纯 HTTP 的 mock/integration 测试以保证关键 contract（特别是 D1 的返回类型）。

---

## E. calibration + QEM + workflows

### E1 [bug · high] `M3Mitigator(calibration_result=ReadoutCalibrationResult(...))` 抛 TypeError
- 文件：`UnifiedQuantum/uniqc/qem/m3.py:91`
- 现象：按 docs 例子调用：
  ```python
  m3 = M3Mitigator(calibration_result=result_1q, max_age_hours=24.0)
  m3.mitigate_counts({"0":80,"1":20})
  # TypeError: 'ReadoutCalibrationResult' object is not subscriptable
  ```
  内部 `cal["confusion_matrix"]` 期待 dict，但顶层 `ReadoutCalibrationResult` 是 dataclass。
- 建议：在 `mitigate_counts/_load_from_cache` 内统一适配 dict 与 dataclass。

### E2 [api · high] `ReadoutCalibrator.calibrate_1q/2q` 返回 `dict` 而非 `ReadoutCalibrationResult`
- 文件：`UnifiedQuantum/uniqc/calibration/readout.py`
- 现象：`cal.calibrate_1q(qubit=0)` 返回 `dict`；但 `docs/source/guide/calibration.md`（英文版）和 skill 都示范 `result.confusion_matrix`（属性式）。两个公开类型并存（dict + dataclass）非常容易踩坑，并直接导致 E1。
- 建议：把 `ReadoutCalibrator` 的返回值改为 `ReadoutCalibrationResult` dataclass；同时让 `M3Mitigator` 接受 dataclass。

### E3 [bug · medium] `ReadoutEM.mitigate_counts` 在 ≥3 qubit 路径下把 bitstring 误当十进制
- 文件：`uniqc/qem/readout_em.py::_mitigate_per_qubit`（≥3 qubit 分支）
- 现象：
  ```python
  em.mitigate_counts({"000":40,"111":60}, measured_qubits=[0,1,2])
  # IndexError: index 111 is out of bounds for axis 0 with size 8
  ```
  `"111"` 被 `int(...)` 当成十进制 111 而非二进制 7。
- 建议：用 `int(bitstring, 2)` 解析，或在外层强制 bitstring→int 的统一函数。

### E4 [inconsistency · medium] `ReadoutEM` 自动校准只覆盖 1q，不覆盖 2q
- 文件：`uniqc/qem/readout_em.py::_mitigate_2q`
- 现象：`em.mitigate_counts({"00":..,"11":..}, measured_qubits=[0,1])` 在缓存空时直接 `FileNotFoundError: ... Run calibration first`；而 1q 路径会自动校准并写缓存。Docs/skill 描述（"wraps ReadoutCalibrator internally and dispatches"）暗示 2q 也会自动校准。
- 建议：让 2q 与 1q 行为对齐；或在 docs 明确「2q 必须先 `run_readout_em_workflow(..., pairs=...)`」。

### E5 [inconsistency · low] `StaleCalibrationError` 仅在 `cache_path` 路径触发
- 文件：`uniqc/qem/m3.py::__init__`
- 现象：`M3Mitigator(calibration_result=stale_result, max_age_hours=1.0)` 不抛异常；只有 `cache_path=...` 才抛。guide §2 「TTL 强制策略」暗示无论怎样构造都强制 TTL。
- 建议：在 `__init__` 收到 `calibration_result` 时也校验 `calibrated_at`。

### E6 [deprecation · low] 例子用了 `datetime.utcnow()`
- 现象：源码与示例均使用 `datetime.utcnow()`，Python 3.12 `DeprecationWarning`。
- 建议：改 `datetime.now(datetime.UTC)`。

---

## F. CLI / config / exceptions / torch

### F1 [bug · medium] `task clear --status <X>` 忽略状态过滤
- 文件：`UnifiedQuantum/uniqc/cli/task.py:151-173`
- 现象：`uniqc task clear --status completed --force` 报告 `Cleared 82 tasks`；无论传 `success / failed / pending / 任意字符串`，调用的都是 `clear_completed_tasks()`。
  ```python
  if status:
      count = clear_completed_tasks()   # 不传 status
  else:
      ...
      clear_cache()
  ```
  另外 `task list --status` 用的是 `pending/running/success/failed`，而 `task clear --status` 文档示例用 `completed`（见 F8），名称也不一致。
- 建议：把 `status` 真的传给 `clear_completed_tasks(status=...)` 并支持 `success/failed`，或直接删掉该选项。

### F2 [doc · low] `result --platform` help 缺 `quark` 和 `dummy`
- 现象：`uniqc result --help` 写 `--platform Platform: originq/quafu/ibm`；但 `submit` 支持 `quark/dummy`，且 `result` 对 dummy 任务实测可查。
- 建议：补全 help 字符串。

### F3 [api · low] `backend show` 用 `:`，`backend chip-display` 用 `/`
- 现象：`backend show originq:WK_C180` 正常；`backend chip-display originq:WK_C180` 报 `Identifier must be in the form 'platform/chip_name'`。同一工具两种 identifier 分隔符。
- 建议：在 `chip-display` 同时接受 `:` 与 `/`；或两边统一。

### F4 [exceptions · low] 多个顶层导出的异常类没有 `raise` 点
- 文件：`uniqc/exceptions.py`
- 现象：`AuthenticationError / QuotaExceededError / InsufficientCreditsError / NetworkError / CircuitTranslationError` 在 `uniqc/` 源码中**没有任何 `raise` 点**；用户写 `try: ... except AuthenticationError` 永远不会命中。
- 建议：要么在云端 adapter 中实际 raise（OriginQ/Quafu 的 401/403 路径），要么从公开接口删除。

### F5 [exceptions · low] `CompilationFailedException / BackendOptionsError / StaleCalibrationError` 不继承 `UnifiedQuantumError`
- 现象：
  - `CompilationFailedException`（`uniqc/compile/_utils.py`）父类 `RuntimeError`
  - `BackendOptionsError`（`uniqc/backend_adapter/task/options`）父类 `ValueError`
  - `StaleCalibrationError`（`uniqc/qem/m3.py`）父类 `Exception`
  用 `except UnifiedQuantumError:` 兜底无法捕到这三类。
- 建议：统一到 `UnifiedQuantumError` 体系；或在文档明确每个异常的实际父类。

### F6 [doc · low] `python -m uniqc` 报 `No module named uniqc.__main__`
- 现象：`python -m uniqc --help` 抛错；只有 `python -m uniqc.cli` 可用。skill / troubleshooting 已强调，但 `docs/source/cli/installation.md` 与 `quickstart.md` 没明确说。
- 建议：补一个 `uniqc/__main__.py` 转发到 `uniqc.cli.main:app`，或在 `cli/installation.md` 顶部加 callout。

### F7 [doc · medium] `docs/guide/pytorch.md` 中 `QuantumLayer` 构造参数已与代码不符
- 文件：`UnifiedQuantum/docs/source/guide/pytorch.md:59-65, 115, 140, 190`
- 现象：文档示例：
  ```python
  layer = QuantumLayer(circuit_template=build_circuit, expectation_fn=expectation,
                       param_names=["theta"], shift=0.5)
  ```
  实际签名 `QuantumLayer(circuit, expectation_fn, n_outputs=1, init_params=None, shift=π/2)`，不接受 `circuit_template=` / `param_names=`（参数名从 `circuit._parameters` 自动取）。按文档跑 `TypeError`。
- 建议：示例改为 `QuantumLayer(circuit=qc, expectation_fn=fn, init_params=torch.zeros(n))`，并说明「参数名称从 `circuit._parameters` 自动获取」。

### F8 [doc · low] `docs/cli/task.md` 写 `task clear --status completed`，与 list 的 status 词表不一致
- 文件：`UnifiedQuantum/docs/source/cli/task.md:51`
- 现象：合法值是 `pending/running/success/failed`，叠加 F1 的 bug，文档示例既看不出 bug 也教不会用户正确状态名。
- 建议：示例换成 `--status success` 或 `task clear --force`；与 F1 一起修。

### F9 [config · low] `uniqc.config` 缺少「按平台标准 key 名」验证
- 文件：`uniqc/config.py:380` 处 quark 兜底兼容 `QUARK_API_KEY` 与 `token`，但其他平台只接受 `token`。如果用户写 `originq.api_key`，`uniqc config validate` 仍判 valid，运行时才报缺 token。
- 建议：在 `validate_config()` 中按 `PLATFORM_REQUIRED_FIELDS` 校验；未知键给 warning。

---

## 总览

| 域 | 高 | 中 | 低 | 备注 |
|----|----|----|----|------|
| A circuit/compile/vis | 2 | 2 | 1 | compile 签名漂移影响 skill |
| B simulators | 0 | 3 | 3 | NoisySim 默认值跑不通；命名冲突 |
| C algorithms | 2 | 1 | 2 | `w_state` / `dicke_state_circuit(k=1)` 算法错误 |
| D backend/cloud | 2 | 5 | 4 | wait_for_result 返回 dict、submit_task 文案错误 |
| E calibration/QEM | 2 | 2 | 2 | M3 dataclass 不兼容、bitstring 解析错误 |
| F CLI/config/torch | 0 | 2 | 7 | task clear bug、QuantumLayer 文档过时 |

**优先建议**
1. 先修 D1 / D2（云提交主路径文案与返回类型）— 直接影响所有云用户。
2. 修 C1 / C2 — 算法静默给错结果。
3. 修 E1 / E2 — QEM 主路径不可用。
4. 文档侧统一 `compile()` 签名（A4）与 `QuantumLayer` 签名（F7）— skill 上多处复制了过时代码片段。
