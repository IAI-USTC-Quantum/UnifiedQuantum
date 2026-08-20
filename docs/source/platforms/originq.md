(platforms-originq)=
# OriginQ 本源量子云

## 简介

OriginQ（本源量子云）提供超导量子计算机真机与多种模拟器后端。uniqc 通过
OriginIR 与其交互——uniqc 的 `Circuit.originir` 原生输出即 OriginIR，
因此 OriginQ 是转换损耗最低的平台。

## 安装

```bash
pip install unified-quantum[originq]
```

`[originq]` extra 安装 `pyqpanda3`（目前仅提供 Python < 3.14 的 wheel）。

## 配置凭证

在本源量子云平台申请 API token 后：

```bash
uniqc config set originq.token <YOUR_TOKEN>
```

## 查看后端

```bash
uniqc backend list -p originq
```

硬件后端如 `WK_C180`（180 比特）、`PQPUMESH8`；另有三种模拟器后端
`full_amplitude`（全振幅）、`partial_amplitude`（部分振幅）、
`single_amplitude`（单振幅），在列表中以 `Type = sim` 标识。

## 提交任务

```bash
uniqc submit circuit.ir --backend originq:WK_C180 --shots 1000 --wait
```

Python：

```python
from uniqc import Circuit, submit_task, wait_for_result

c = Circuit()
c.h(0)
c.cnot(0, 1)
c.measure(0)
c.measure(1)

task_id = submit_task(c, backend="originq:WK_C180", shots=1000)
print(wait_for_result(task_id))
```

## 平台约定与限制

- 输入格式：OriginIR 字符串，由 `OriginQCircuitAdapter` 自动转换。
- 提交为**异步**：`submit()` 立即返回任务 ID，用 `wait_for_result()`
  阻塞等待结果。
- 支持完整的 OriginIR 门集（含 `RPhi`、`UU15`、`CONTROL`/`DAGGER` 块等），
  详见 {ref}`平台约定 <platform-gate-support>`。
- 结果为扁平 `{bitstring: shots}` counts，bitstring 序遵循
  {ref}`统一 endianness 约定 <platform-bit-endianness>`。
