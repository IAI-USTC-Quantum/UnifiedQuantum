# pytest 测试指南

`uniqc/test/` 是 UnifiedQuantum 的 pytest 测试套件。测试文件使用
`test_*.py`，pytest 同时收集 `test_*` 和 `run_test_*` 函数；测试类使用
`Test*` 或 `RunTest*`。辅助函数不得使用这些前缀，以免被误收集。

不要以 `@uniq_test` 是否存在判断测试是否正式。该旧装饰器不是收集条件，也不
代表当前套件的覆盖范围。

## 常用命令

```bash
# 默认离线套件；所有 cloud 标记测试都会跳过
uv run pytest uniqc/test

# 单个测试
uv run pytest uniqc/test/core/test_originir_parser.py::run_test_originir_parser -v

# 一个目录或一个 marker 组
uv run pytest uniqc/test/circuit_builder -v
uv run pytest uniqc/test -m "requires_cpp" -v

# 执行云测试（需要对应 SDK、凭证和网络）
uv run pytest uniqc/test --real-cloud-test -m cloud -v
```

`pytest.ini` 中的 `testpaths = uniqc/test` 是默认收集根；直接运行
`pytest` 时也会使用它。使用 `--collect-only -q` 可在当前环境中查看实际收集
结果，不要在文档中维护会随测试演进而过期的固定数量。

## 云测试与依赖 marker

所有 `@pytest.mark.cloud` 和 `@pytest.mark.real_cloud_execution` 测试默认跳过。
只有传入 `--real-cloud-test` 才会解除该总开关；对应 SDK 和凭证 marker 仍然会
独立检查。因此 CI 和本地默认命令均不会访问云端或创建真实任务。

| Marker | 作用 |
| --- | --- |
| `cloud` | 需要真实网络或云平台凭证；默认跳过。 |
| `real_cloud_execution` | 会提交真实量子线路；默认跳过。 |
| `requires_pyqpanda3` | 需要 OriginQ SDK。 |
| `requires_qiskit` | 需要 Qiskit 与 IBM Runtime。 |
| `requires_quafu` | 需要 legacy `pyquafu` SDK。 |
| `requires_pytorch` | 需要 PyTorch。 |
| `requires_torchquantum` | 需要 PyTorch 和 TorchQuantum。 |
| `requires_cpp` | 需要编译后的 `uniqc_cpp` 扩展。 |
| `requires_originq_credentials` | 需要 OriginQ token。 |
| `requires_quafu_credentials` | 需要 Quafu token。 |
| `requires_quark_credentials` | 需要 Quark token。 |
| `requires_ibm_credentials` | 需要 IBM token。 |

使用 `dummy:<provider>:<chip>` 的测试不提交云任务，但仍依赖该 provider 的 SDK
和 chip cache。此类测试必须**显式**添加相应的 `requires_*` marker（并在需要
token 或网络时添加 `cloud`/凭证 marker）；`conftest.py` 不会猜测或自动补标记。

## CI 与维护

- `build_and_test.yml` 运行默认离线 pytest、专门的第一方警告 gate，以及
  `ruff check .`。
- `pytest_coverage.yml` 是 coverage artifact 与 Codecov 的唯一权威 workflow。
- 新增测试应优先使用真实的 `test_*` 命名和精确 marker；完全 mock 的网络单元
  测试不应标记为 `cloud`。
- 提交前至少运行与改动相邻的测试；改动公共 Python 代码时运行
  `uv run ruff check .`。
