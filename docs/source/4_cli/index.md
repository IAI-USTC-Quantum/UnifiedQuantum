# CLI 介绍

UnifiedQuantum 的 CLI 入口是 ``uniqc``（由 ``uv tool install unified-quantum`` 全局安装），
等价的模块入口是 ``python -m uniqc.cli``。

本页只列目录索引；子命令一览、自动 walkthrough、dummy backend id 命名规则在
[CLI 完整 walkthrough](walkthrough.md)。常见工作流模板与 FAQ 在
[完整工作流与常见问题](workflow.md)。

## 入门与全局示例

```{toctree}
:maxdepth: 1

installation
doctor
walkthrough
workflow
```

## 线路与执行

```{toctree}
:maxdepth: 1

simulate
submit
result
circuit
draw
```

## 配置与任务

```{toctree}
:maxdepth: 1

config
sync
task
backend
```

## 校准与服务

```{toctree}
:maxdepth: 1

calibrate
gateway
```

## 相关章节

CLI 只是 UnifiedQuantum 的一面；每个子命令背后都有对应的 Python API 文档：

- [基本用法](../1_basic_usage/index.md) —— 线路构建、模拟、提交任务的 API 全景
- [进阶主题](../2_advanced/index.md) —— 编译、噪声、校准等 CLI 参数背后的机制
- [云平台指南](../platforms/index.md) —— 各平台的凭证、SDK 与后端差异
- [API 参考](../6_api/index.md) —— `uniqc` 包的完整符号索引
