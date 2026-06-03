# 基本用法

构造电路、本地模拟、提交到 dummy 或真机、读取并后处理结果——这一章覆盖"从空电路到
真机结果"的主路径。本页只列目录索引，每一节的内容都在下方子页面里。

## 主路径走读

```{toctree}
:maxdepth: 1

walkthrough
```

[主路径走读](walkthrough.md) 把 **构造电路 → 本地模拟 → 提交并后处理 → 配置 → 可视化**
五件事按顺序串一遍，每节都来自 ``examples/1_basic_usage/0X_*.py`` 自动生成的示例。

## 主要 API

```{toctree}
:maxdepth: 1

main_api
```

[主要 API](main_api.md) 把基本用法部分用到的函数 / 类按用途分组：每行同时给出
API 参考链接和它在用户文档中实际出现的章节，避免出现"API 参考"这种空指向。

## 深度文档

下列页面是从原 `guide/` 章节迁移过来的深度文档，分别对应"构造电路 → 模拟 → 提交 →
任务管理 → PyTorch → 平台约定"完整链路。

```{toctree}
:maxdepth: 1

circuit
originir
originir_official
originir_relationship
qasm
simulation
submit_task
task_manager
pytorch
platform_conventions
best_practices
```
