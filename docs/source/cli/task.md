# 任务管理 (`uniqc task`)

管理已提交的任务。

## 列出任务

```bash
# 列出所有任务
uniqc task list

# 按状态筛选
uniqc task list --status success
uniqc task list --status failed

# 按平台筛选
uniqc task list --platform originq

# 限制显示数量
uniqc task list --limit 10
```

表格输出示例：

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Tasks                              ┃
┡━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━┩
│ Task ID    │ Platform │ Status │ Shots │ Submit Time    │
├────────────┼──────────┼────────┼───────┼────────────────┤
│ TASK001    │ originq  │ success│ 1000  │ 2026-04-18 10: │
│ TASK002    │ originq  │ running│ 2000  │ 2026-04-18 11: │
└────────────┴──────────┴────────┴───────┴────────────────┘
```

## 查看任务详情

```bash
# 显示任务详情
uniqc task show TASK_ID

# JSON 格式输出
uniqc task show TASK_ID --format json
```

## 清理任务缓存

```bash
# 清理已完成的任务
uniqc task clear --status completed

# 清理所有缓存（需确认）
uniqc task clear

# 强制清理（无需确认）
uniqc task clear --force
```
