# 最佳实践

12 个发布前**可重跑的完整场景**：从配置/缓存、构造电路、编译、API/CLI 提交、变分线路、
Torch 集成，到 calibration + QEM、XEB workflow。每一个都对应
``examples/3_best_practices/<n>_*.py``，并由 ``scripts/build_docs.py`` 在文档构建时
按 ``[doc-require:]`` 门控自动重跑。

## 覆盖矩阵

| 案例 | 配置 | 后端缓存 | 裸 Circuit | Named | 虚拟/本地后端 | API 提交 | CLI 提交 | 可视化 | 变分 | Torch | Calibration/QEM |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 00 配置与后端缓存 | ✓ | ✓ |  |  | ✓ |  |  |  |  |  |  |
| 01 裸线路模拟 |  |  | ✓ |  | ✓ |  |  | ✓ |  |  |  |
| 02 Named Circuit |  |  | ✓ | ✓ | ✓ |  |  | ✓ |  |  |  |
| 03 编译与虚拟后端 |  |  | ✓ |  | ✓ |  |  |  |  |  |  |
| 04 API 提交 |  |  | ✓ |  | ✓ | ✓ |  | ✓ |  |  |  |
| 05 CLI 提交 |  |  | ✓ |  | ✓ |  | ✓ |  |  |  |  |
| 06 云后端模板 | ✓ |  | ✓ |  | ✓ | ✓ | ✓ |  |  |  |  |
| 07 变分线路 |  |  | ✓ |  | ✓ |  |  | ✓ | ✓ |  |  |
| 08 Torch 集成 |  |  | ✓ |  | ✓ |  |  | ✓ | ✓ | ✓ |  |
| 09 Calibration + QEM |  |  |  |  | ✓ |  |  | ✓ |  |  | ✓ |
| 10 XEB workflow |  |  | ✓ |  | ✓ |  |  | ✓ |  |  | ✓ |
| 11 原生 Torch 训练 |  |  | ✓ |  | ✓ |  |  | ✓ | ✓ | ✓ |  |

## 案例

```{include} ../_generated/examples/3_best_practices/00_config_and_backend_cache.md
```

```{include} ../_generated/examples/3_best_practices/01_bare_circuit_simulation.md
```

```{include} ../_generated/examples/3_best_practices/02_named_circuit_and_reuse.md
```

```{include} ../_generated/examples/3_best_practices/03_compile_region_dummy_backend.md
```

```{include} ../_generated/examples/3_best_practices/04_api_submit_dummy_result.md
```

```{include} ../_generated/examples/3_best_practices/05_cli_workflow_dummy.md
```

```{include} ../_generated/examples/3_best_practices/06_cloud_backend_template.md
```

```{include} ../_generated/examples/3_best_practices/07_variational_circuit.md
```

```{include} ../_generated/examples/3_best_practices/08_torch_quantum_training.md
```

```{include} ../_generated/examples/3_best_practices/09_calibration_qem_dummy.md
```

```{include} ../_generated/examples/3_best_practices/10_xeb_workflow_dummy.md
```

```{include} ../_generated/examples/3_best_practices/11_native_torch_training.md
```

## 发布前重跑

维护者发布前应该用全开发环境重跑一次完整 docs 流水线（含 pre-doc-execution）：

```bash
uv sync --all-extras --group dev --group docs --upgrade
cd docs
uv run make html
```

如果某个示例因为缺少依赖或凭据无法执行，``scripts/build_docs.py`` 会**跳过**而不是
失败；请保证至少 ``dummy:local:*`` 路径全部 pass。如果某个示例真的产生了 warning /
error 而它本应被忽略（比如来自某个第三方库的 deprecation），用
``[doc-warning-ignore: <regex>]`` 在示例 docstring 里标注即可。
