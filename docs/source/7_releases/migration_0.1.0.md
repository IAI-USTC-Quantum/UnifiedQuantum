# 0.1.0 迁移指南

`0.1.0` 按[弃用政策](deprecation_policy.md)移除了所有在 `0.0.x` 期间触发
`DeprecationWarning` 的公共 API。本页给出每个移除项的 before/after 对照。
从 `0.0.x` 升级时，先在你的代码库运行
`pytest -W error::DeprecationWarning`（或直接搜索下文 left 列的写法），
逐项替换即可。

## Quafu 平台 → Quark

Quafu 平台支持整体移除：`quafu_adapter` 模块、`QuafuBackend`、
`QuafuCircuitAdapter`、`QuafuOptions`、`normalize_quafu`、`Platform.QUAFU`、
CLI / 网关 / 后端发现中的 quafu 分支、`quafu.*` 配置键，以及 `pyquafu`
依赖。BAQIS ScQ 芯片由 Quark 平台承接。

```python
# Before (0.0.x)
backend = get_backend("quafu:ScQ-P10")      # quafu:<chip>

# After (0.1.0)
# pip install unified-quantum[quark]
backend = get_backend("quark:<chip>")       # quark:<chip>
```

## `uniqc.simulator.get_backend()` → `get_simulator` / `create_simulator`

```python
# Before (0.0.x)
from uniqc.simulator import get_backend
sim = get_backend("statevector")

# After (0.1.0) — 参数相同
from uniqc.simulator import get_simulator   # 或 create_simulator
sim = get_simulator("statevector")
```

顶层的 `uniqc.get_backend()`（云后端工厂）**不受影响**。

## `IBMAdapter` → `QiskitAdapter`

```python
# Before (0.0.x)
from uniqc.backend_adapter.task.adapters.ibm_adapter import IBMAdapter
adapter = IBMAdapter(proxy=...)

# After (0.1.0) — 同样的 proxy= 构造签名，同样基于 qiskit-ibm-runtime
from uniqc.backend_adapter.task.adapters.qiskit_adapter import QiskitAdapter
adapter = QiskitAdapter(proxy=...)
```

`ibm_adapter` 模块本身保留（其中的标定数据辅助函数仍被 `QiskitAdapter`
使用），只是 `IBMAdapter` 类被移除。

## 平台原生 task id 查询回退 → uniqc 内部 task id

查询接口（`query_task` / `get_platform_task_ids` 等）不再把平台原生
task id 经 shard 索引隐式解析到 `uqt_*` 父任务。

```python
# Before (0.0.x)
result = query_task("<platform-native-id>")     # 隐式回退解析到 uqt_* 任务

# After (0.1.0) — 使用提交时返回的 uniqc 内部 id
task_id = submit_task(...)                      # 形如 "uqt_*"
result = query_task(task_id)
```

显式传入 `backend=` 的 legacy 直连查询路径不受影响；shard 索引本身
（`TaskStore.find_uniqc_id_by_platform_id`）保留。

## 算法构件：in-place 旧形式 → fragment + `add_circuit`

以下 12 个函数不再接受 `Circuit` 作为首参做就地突变，统一收敛为
fragment 形式 `f(n_qubits, ...) -> Circuit`：

`qft_circuit`、`deutsch_jozsa_circuit`、`dicke_state_circuit`、
`thermal_state_circuit`、`cluster_state`、`ghz_state`、`w_state`、
`amplitude_estimation_circuit`、`grover_oracle`、`grover_diffusion`、
`grover_operator`、`vqd_circuit`。

```python
# Before (0.0.x) — 就地突变，返回 None
c = Circuit(3)
qft_circuit(c, qubits=[0, 1, 2])

# After (0.1.0) — 返回新 fragment，用 add_circuit 组合
c = Circuit(3)
c.add_circuit(qft_circuit(3, qubits=[0, 1, 2]))
# 或直接用 fragment 本身：
c = qft_circuit(3)
```

Grover 全家桶同理：

```python
# Before (0.0.x)
c = Circuit()
for q in range(n):
    c.h(q)
anc = grover_oracle(c, marked_state=5, qubits=list(range(n)))  # 返回 ancilla 下标
grover_diffusion(c, qubits=list(range(n)))

# After (0.1.0) — fragment 形式；ancilla 默认为 max(qubits) + 1
c = Circuit()
for q in range(n):
    c.h(q)
c.add_circuit(grover_oracle(marked_state=5, qubits=list(range(n))))
c.add_circuit(grover_diffusion(qubits=list(range(n))))
```

各函数签名要点：

- 态制备类（`qft_circuit` / `dicke_state_circuit` / `thermal_state_circuit`
  / `ghz_state` / `w_state` / `cluster_state`）：首参为
  `n_qubits: int | None`；为 `None` 时若给了 `qubits` 列表则推断为
  `max(qubits) + 1`。
- oracular 类（`deutsch_jozsa_circuit` / `grover_oracle` /
  `amplitude_estimation_circuit` / `grover_operator`）：首参为 oracle
  `Circuit`（`grover_oracle` 首参为 `marked_state: int`）。
- `grover_diffusion(n_qubits=None, *, qubits=None)`：`qubits=None` 时默认
  `[0, 1]`（或 `range(n_qubits)`）。
- `vqd_circuit(n_qubits, *, ansatz_params, prev_states, ...)`：等价于
  `vqd_ansatz` 的 fragment 包装。

## `grover_diffusion(..., ancilla=...)` 参数删除

该参数自引入起就无效果（diffusion 不需要 ancilla），`0.1.0` 已将其删除。

```python
# Before (0.0.x)
grover_diffusion(c, qubits=[0, 1, 2], ancilla=3)

# After (0.1.0) — 直接去掉 ancilla，并用 fragment 形式
c.add_circuit(grover_diffusion(qubits=[0, 1, 2]))
```
