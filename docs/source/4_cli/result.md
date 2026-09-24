# 结果查询 (`uniqc result`)

查询已提交任务的结果（对应 Python API {py:func}`query_task() <uniqc.backend_adapter.task_manager.query_task>` 与 {py:func}`wait_for_result() <uniqc.backend_adapter.task_manager.wait_for_result>`）。

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
