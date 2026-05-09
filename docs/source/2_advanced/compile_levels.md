# 编译策略：`local_compile` 与 `cloud_compile`

uniqc 在 `submit_task` / `submit_batch` / `dry_run_task` 中通过两个**整数**关键字参数来描述编译流水线：

- `local_compile: int = 1` —— 本地（qiskit）层的优化等级
- `cloud_compile: int = 1` —— 云端编译器的请求强度

这两个参数互相独立，分别决定客户端侧和云端侧的处理。

## 不会被绕过的硬规则：IR 兼容性校验

无论 `local_compile` / `cloud_compile` 取何值，uniqc 永远会在提交前执行 **IR 语言兼容性校验**：

- 提交到 OriginQ 平台只能是 OriginIR
- 提交到 Quafu / IBM 平台只能是 OpenQASM 2.0

这一层规则是“硬阻塞”，发现不兼容立即抛 `UnsupportedGateError`，不会静默放行。

## `local_compile`（本地编译）

| 值 | 含义 |
| --- | --- |
| `0` | **跳过** 本地 qiskit transpile。线路按原样发送，软兼容性校验仅打印 warning。|
| `1` | qiskit `optimization_level=1`（默认，温和优化、正确性优先） |
| `2` | qiskit `optimization_level=2` |
| `3` | qiskit `optimization_level=3`（重型优化，编译时间长） |

底层调用 `compile_for_backend(circuit, backend, level=local_compile)`。

## `cloud_compile`（云端编译）

云端编译能力因平台而异。uniqc 对适配器的最小约定是：

| 值 | 含义 |
| --- | --- |
| `0`  | 请求云端 **关闭** 自动编译（`circuit_optimize=False`）。线路按提交内容直接执行。|
| `>0` | 请求云端 **开启** 自动编译（`circuit_optimize=True`）。具体强度由平台决定。|

部分平台未来可能支持更细的等级；那时适配器可以读取整数值本身。当前所有适配器只关心是否 `> 0`。

## 何时选择什么？

- 想要“**完全交给云端**” → `local_compile=0, cloud_compile=1`
- 想要“**完全本地控制，云端只跑硬件门**” → `local_compile=3, cloud_compile=0`
- 想做**调试 / dry-run**，验证 IR 与你写的完全一致 → 两边都 `=0`
- 默认（`1, 1`）适用于绝大多数日常实验

## 示例

```python
from uniqc import submit_task

# 本地温和优化 + 云端关闭自动编译
task_id = submit_task(
    circuit,
    backend="originq:WK_C180",
    shots=1024,
    local_compile=1,
    cloud_compile=0,
)

# 本地不编译，把原始 IR 交给云端做编译
task_id = submit_task(
    circuit,
    backend="originq:WK_C180",
    shots=1024,
    local_compile=0,
    cloud_compile=1,
)
```

## 与旧参数的关系（pre-release 期间打破兼容）

旧的 `auto_compile: bool` / `skip_validation: bool` 已被移除，不再接受。等价映射：

| 旧 | 新 |
| --- | --- |
| `auto_compile=True`  | `local_compile=1` |
| `auto_compile=False` | `local_compile=0` |
| `skip_validation=True` | （不再需要；`local_compile=0` 时校验自动降级为 warning，硬规则仍生效） |
