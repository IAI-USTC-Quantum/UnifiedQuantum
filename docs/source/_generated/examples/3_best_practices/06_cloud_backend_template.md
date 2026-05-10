### 06 — 云后端提交模板与 dry-run

*Source*: ``examples/3_best_practices/06_cloud_backend_template.py``  
*Status*: **skip** — missing requirements: originq (pyqpanda3 + originq token configured)

展示真实后端路径的安全模板：先 ``dry_run_task``，再提交。该例子默认仅执行 dummy
dry-run；真实 OriginQ / Quafu / IBM 提交单元应在维护者确认 token、账号额度和后端

**Source code**

```{literalinclude} ../../../examples/3_best_practices/06_cloud_backend_template.py
:language: python
```

:::{note}
Example skipped during pre-doc-execution: missing requirements: originq (pyqpanda3 + originq token configured)
:::

