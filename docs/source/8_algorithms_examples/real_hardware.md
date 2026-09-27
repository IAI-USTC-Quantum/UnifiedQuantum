# 真实硬件实验

在真实量子芯片上运行需要面对读出误差、相干性退化等工程挑战。
本节以 OriginQ WK180 芯片为例，演示读出误差缓解（Readout EM）和
交叉熵基准测试（XEB）。

## 示例

```{include} ../_generated/examples/2_advanced/wk180__readout_em.md
```

```{include} ../_generated/examples/2_advanced/wk180__xeb.md
```

## 相关页面

- [芯片校准与量子错误缓解](../2_advanced/calibration.md) —— Readout EM 与 XEB 的完整 API
- [OriginQ 平台指南](../platforms/originq.md) —— WK180 芯片的接入与凭证配置
- [dummy 平台](../platforms/dummy.md) —— 用 `dummy:originq:WK_C180` 在本地复演真机实验
- [CLI calibrate 命令](../4_cli/calibrate.md) —— 本页工作流的命令行版本
