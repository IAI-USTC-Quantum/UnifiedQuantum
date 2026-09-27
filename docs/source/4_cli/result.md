# 结果查询 (`uniqc result`)

查询已提交任务的结果。

## 基本用法

```bash
# 查询任务结果
uniqc result TASK_ID --platform originq

# 等待任务完成
uniqc result TASK_ID --platform originq --wait

# 设置超时时间
uniqc result TASK_ID --platform originq --wait --timeout 600
```

## 输出格式

```bash
# 表格输出（默认）
uniqc result TASK_ID --platform originq

# JSON 输出
uniqc result TASK_ID --platform originq --format json
```

表格输出示例：

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Result for TASK123456    ┃
┡━━━━━━━┳━━━━━━━┳━━━━━━━━━┩
│ State │ Count │ Prob    │
├───────┼───────┼─────────┤
│ 00    │ 487   │ 48.7%   │
│ 11    │ 513   │ 51.3%   │
└───────┴───────┴─────────┘
```

## 相关文档

- [提交任务](submit.md) —— 先提交才有任务 ID；backend 命名规则也在此页
- [任务管理器](../1_basic_usage/task_manager.md) —— Python 侧的提交 / 轮询 / 结果管理
- [平台约定 · 输出格式](platform-output-formats) —— counts 的 bitstring 端序与结果字段约定
- [本地模拟](simulate.md) —— 不需要云端任务时直接在本地运行
