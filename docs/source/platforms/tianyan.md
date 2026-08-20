(platforms-tianyan)=
# 天衍量子计算云平台（tianyan）

## 简介

天衍是中电信量子集团的量子计算云平台，提供超导量子计算机真机与多种
仿真机。uniqc 通过天衍官方 SDK `cqlib` 接入，线路以 **QCIS** 格式提交。

## 安装

```bash
pip install unified-quantum[tianyan]
```

## 配置凭证

在天衍平台官网 [qc.zdxlz.com](https://qc.zdxlz.com) 注册账号并申请
登录密钥后：

```bash
uniqc config set tianyan.login_key <YOUR_LOGIN_KEY>
```

## 查看后端

```bash
uniqc backend list -p tianyan
```

常见机器名：

| 机器名 | 类型 |
|--------|------|
| `tianyan176` | 真机（QPU） |
| `tianyan_sw` | 全振幅仿真 |
| `tianyan_sa` | 单振幅仿真 |
| `tianyan_s` | 稳定子（stabilizer）仿真 |
| `tianyan_tn` | 张量网络仿真 |
| `tianyan_tnn` | 带噪声张量网络仿真 |

实际可用列表以 `uniqc backend list -p tianyan` 输出为准。

## 提交任务

```bash
uniqc submit circuit.ir --backend tianyan:tianyan176 --shots 1000 --wait
```

Python：

```python
from uniqc import Circuit, submit_task, wait_for_result

c = Circuit()
c.h(0)
c.cnot(0, 1)
c.measure(0)
c.measure(1)

task_id = submit_task(c, backend="tianyan:tianyan176", shots=1000)
print(wait_for_result(task_id))
```

## 平台约定与限制

- 提交格式为 **QCIS**，由 `TianyanCircuitAdapter` 从内部 `Circuit` 自动转换。
- 结果按**测量比特标签序**归一为 `{bitstring: shots}` counts，并遵循
  {ref}`统一 endianness 约定 <platform-bit-endianness>`
  （bitstring 最右字符对应 `c[0]`，即第一次 `measure()` 写入的比特）。
- 真机与仿真机的可用性、排队状态以平台实时状态为准。
