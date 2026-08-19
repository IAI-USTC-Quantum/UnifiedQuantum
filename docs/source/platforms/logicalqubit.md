(platforms-logicalqubit)=
# 逻辑比特超导量子云平台（logicalqubit）

## 简介

逻辑比特（LogicalQubit）超导量子云平台提供 AGate 系列超导量子芯片
（如 30 / 100 比特规格）。uniqc 通过官方 SDK `lqcloud`（≥ 0.4.2）接入。

## 安装

```bash
pip install unified-quantum[logicalqubit]
```

## 配置凭证

```bash
uniqc config set logicalqubit.api_key <YOUR_API_KEY>
```

可选：自定义服务地址（默认 `https://cloud.logicalqubit.com`）：

```bash
uniqc config set logicalqubit.url https://cloud.logicalqubit.com
```

## 查看后端

```bash
uniqc backend list -p logicalqubit
```

芯片为 AGate 系列（如 30 / 100 比特规格），具体后端名以
`uniqc backend list -p logicalqubit` 输出为准。

## 提交任务

```bash
uniqc submit circuit.ir --backend logicalqubit:<chip> --shots 1000 --wait
```

Python：

```python
from uniqc import Circuit, submit_task, wait_for_result

c = Circuit()
c.h(0)
c.cnot(0, 1)
c.measure(0)
c.measure(1)

task_id = submit_task(c, backend="logicalqubit:<chip>", shots=1000)
print(wait_for_result(task_id))
```

## 平台约定与限制

- 单次提交 **shots ≤ 50000**，超出会被拒绝；需要更多采样请分批提交。
- 平台原生结果为 **qiskit 风格大端 bitstring** 的 counts，normalizer 会
  改写为 uniqc 的
  [统一 endianness 约定](../1_basic_usage/platform_conventions.md#platform-bit-endianness)
  （bitstring 最右字符对应 `c[0]`）。
- 门集为 qiskit 风格，转换由 `LogicalQubitCircuitAdapter` 自动完成。
