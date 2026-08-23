(platforms-index)=
# 云平台

本章按平台给出接入指南：安装、凭证配置、后端查询与任务提交。通用的
输入/输出约定、bitstring 序、提交前校验等见
[平台约定](../1_basic_usage/platform_conventions.md)；提交 API 的完整说明见
[提交任务到量子云平台](../1_basic_usage/submit_task.md)。

## 平台总览

| 平台 | key | pip extra | 凭证字段 | 内容 |
|------|-----|-----------|----------|------|
| OriginQ 本源量子云 | `originq` | `unified-quantum[originq]` | `originq.token` | 超导 QPU + 三种模拟器 |
| QuarkStudio | `quark` | `unified-quantum[quark]` | `quark.QUARK_API_KEY` | Quark 云平台 |
| IBM Quantum | `ibm` | 无需 extra（qiskit 为核心依赖） | `ibm.token` | IBM Quantum 后端与模拟器 |
| 天衍量子计算云平台 | `tianyan` | `unified-quantum[tianyan]` | `tianyan.login_key` | 中电信量子，真机 + 多种仿真机 |
| 逻辑比特超导量子云平台 | `logicalqubit` | `unified-quantum[logicalqubit]` | `logicalqubit.api_key`（+ 可选 `logicalqubit.url`） | AGate 系列超导芯片 |
| Dummy 本地模拟 | `dummy` | 无需 extra | 无需凭证 | 本地无噪/含噪模拟 |

想给 UnifiedQuantum 接入一个新云平台？见
[添加一个新云平台](../2_advanced/adding_a_platform.md)。

## 各平台页面

```{toctree}
:maxdepth: 1

originq
quark
ibm
tianyan
logicalqubit
dummy
```
