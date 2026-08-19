(platforms-quark)=
# QuarkStudio（Quark 云平台）

## 简介

QuarkStudio 提供 Quark 系列量子计算后端，uniqc 通过 `quarkstudio` /
`quarkcircuit` SDK 接入，线路经 `QuarkCircuitAdapter` 转换后提交。

## 安装

```bash
pip install unified-quantum[quark]
```

```{note}
`quarkstudio` / `quarkcircuit` 目前只提供 Linux/macOS x86 的 wheel，且要求
Python ≥ 3.12、< 3.14；Windows 与其它平台请改用源码方式或换用其它平台。
```

## 配置凭证

```bash
uniqc config set quark.QUARK_API_KEY <YOUR_API_KEY>
```

（旧字段名 `quark.token` 仍被兼容读取，但新配置请用 `QUARK_API_KEY`。）

## 查看后端

```bash
uniqc backend list -p quark
```

## 提交任务

```bash
uniqc submit circuit.ir --backend quark:<chip> --shots 1000 --wait
```

Python：

```python
from uniqc import Circuit, submit_task, wait_for_result

c = Circuit()
c.h(0)
c.cnot(0, 1)
c.measure(0)
c.measure(1)

task_id = submit_task(c, backend="quark:<chip>", shots=1000)
print(wait_for_result(task_id))
```

其中 `<chip>` 为 `uniqc backend list -p quark` 列出的后端名。

## 平台约定与限制

- 提交语言为 QASM 2.0，由 CircuitAdapter 自动转换。
- 提交前校验按 `cz + sx + rz` 基础门集进行，详见
  [平台约定](../1_basic_usage/platform_conventions.md#platform-precheck)。
- 结果为扁平 `{bitstring: shots}` counts，bitstring 序遵循
  [统一 endianness 约定](../1_basic_usage/platform_conventions.md#platform-bit-endianness)。
