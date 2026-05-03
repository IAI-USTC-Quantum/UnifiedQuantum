# 测试设计与规范

## 目录结构

```
uniqc/test/
├── core/                # 核心解析测试
├── circuit_builder/     # 电路构建测试
├── algorithmics/        # 算法电路测试
│   ├── circuits/        # 电路组件测试
│   ├── measurement/     # 测量测试
│   └── state_preparation/ # 态制备测试
├── simulator/           # 模拟器测试
├── cloud/               # 云平台测试
│   └── platforms/       # 平台配置测试
├── transpiler/          # 转译器测试
├── adapter/             # 适配器测试
├── analyzer/            # 分析器测试
├── benchmark/           # 基准测试
└── integration/         # 集成测试
```

## 核心原则

**只有被 `@uniq_test` 装饰器修饰的函数才是需要执行的正式测试。**

`@uniq_test` 会打印测试开始/结束信息，用于 CI 识别和人类阅读。

## 命名规范

### 正式测试函数
- 命名格式：`run_test_<功能名>`
- 必须被 `@uniq_test('<描述>')` 修饰
- pytest 会自动收集所有 `run_test_*` 函数

### 辅助函数（内部使用）
- 命名格式：`<功能名>`（不带前缀）或 `_<功能名>`
- 不带 `@uniq_test` 装饰器
- 被正式测试函数内部调用，不直接暴露给 pytest

## 测试执行入口

```python
# 通过 pytest 运行全部（推荐）
pytest uniqc/test/ -v

# 运行特定类别
pytest uniqc/test/core/ -v
pytest uniqc/test/simulator/ -v

# 单独运行某个测试
python -m pytest uniqc/test/core/test_originir_parser.py::run_test_originir_parser -v

# 通过 run_test() 运行全部（旧方式，已废弃）
from uniqc.test import run_test
run_test()
```

## 当前测试项清单

| 测试文件 | 正式测试函数 | 说明 |
|---------|------------|------|
| `core/test_general.py` | `run_test_general()` | 通测占位（当前为空） |
| `core/test_originir_parser.py` | `run_test_originir_parser()` | OriginIR 解析器 |
| `core/test_qasm_parser.py` | `run_test_qasm_parser()` | OpenQASM2 解析器 |
| `cloud/test_demos.py` | `run_test_demos()` | OriginQ 远程任务示例 |
| `cloud/test_result_adapter.py` | `run_test_result_adapter()` | 结果适配器 |
| `simulator/test_simulator.py` | `run_test_simulator()` | 噪声模拟器 |
| `simulator/test_random_QASM.py` | `run_test_random_qasm_*` | 随机 QASM 电路（4个测试） |
| `simulator/test_random_OriginIR.py` | `run_test_random_originir_density_operator()` | 随机 OriginIR 电路 |
| `simulator/test_random_QASM_measure.py` | `run_test_random_qasm_compare_shots()` | 随机电路 shot 对比 |
| `benchmark/test_QASMBench.py` | `run_test_qasm()` | QASMBench 电路集 |

**pytest 共收集 14 个正式测试函数。**

## pytest 配置说明

```ini
[pytest]
testpaths = uniqc/test
python_files = test_*.py
python_functions = run_test_*
addopts = -v
```

- `python_functions = run_test_*` 确保只收集正式测试，不收集辅助函数
- 辅助函数不应以 `run_test_` 或 `test_` 开头，避免被 pytest 误收集

## CI 配置说明

- **Build-and-test workflow**：使用 `pytest uniqc/test/ -v -m "not cloud"`
- **Pytest Coverage workflow**：使用 `pytest uniqc/test/ -v -m "not cloud"`

两个 workflow 现已统一使用 pytest。

## 当前测试口径

默认开发环境应通过 `uv sync --all-extras --group dev --group docs` 安装完整依赖。因此，除明确的 `cloud` 集成测试和当前已知的 `torchquantum` 缺失问题外，测试不应因为 `qiskit`、`qutip`、`pyqpanda3`、`quafu`、`torch` 或本地 simulator 缺失而被跳过。此类依赖缺失应暴露为环境问题，而不是被静默 skip。

推荐的本地/CI 默认口径：

```bash
uv run pytest uniqc/test -m "not cloud"
```

当前默认口径下只允许以下 skip：

- `torchquantum not installed`：known issue，覆盖 TorchQuantum 相关测试。

`@pytest.mark.cloud` 只用于真实云平台或真实网络依赖场景，包括：

- 需要真实 `~/.uniqc/config.yaml` token 的 OriginQ、Quafu、IBM submit/query 或 backend connectivity。
- 真实 IBM endpoint 连通性检查。
- 真实 proxy 行为检查，包括配置 proxy 可用性和不可达 proxy 的失败路径。

不应标记为 `cloud` 的测试：

- 只验证 YAML token 读取、proxy 参数构造、错误返回结构的单元测试。
- HTTP/socket 已完全 mock 的网络工具测试。
- 只依赖默认 dev 依赖包的电路翻译、模拟、转译、矩阵和 adapter 单元行为。

## Cloud Tests

Tests marked with `@pytest.mark.cloud` require real cloud credentials and network access.

### Running Cloud Tests Locally

```bash
# Set required credentials in ~/.uniqc/config.yaml
uniqc config set originq.token "your-key"
uniqc config set quafu.token "your-token"
uniqc config set ibm.token "your-token"

# Run cloud tests
pytest uniqc/test/ -v -m cloud

# Run specific platform tests
pytest uniqc/test/ -v -m "cloud and requires_pyqpanda3"

# Run IBM real network/proxy checks only
pytest uniqc/test/cloud/test_network_utils.py -v -m cloud
```

IBM proxy cloud tests read `ibm.proxy` from `~/.uniqc/config.yaml` when testing a configured proxy. The unreachable-proxy test uses a closed localhost port to verify failure handling through the real network stack without depending on an external proxy service.

### CI Behavior

Cloud tests are **skipped by default in CI** via `-m "not cloud"` to avoid:
- Exposing credentials in CI logs
- Incurring cloud platform costs
- Network dependency failures

## Dependency-Specific Tests

Tests may be marked with dependency markers:

| Marker | Description |
|--------|-------------|
| `@pytest.mark.requires_cpp` | Requires compiled C++ backend (uniqc_cpp) |
| `@pytest.mark.requires_pytorch` | Requires PyTorch |
| `@pytest.mark.requires_torchquantum` | Requires TorchQuantum |
| `@pytest.mark.requires_qiskit` | Requires Qiskit |
| `@pytest.mark.requires_quafu` | Requires Quafu/pyquafu |
| `@pytest.mark.requires_pyqpanda3` | Requires pyqpanda3 |

These tests will be skipped if the dependency is not installed.
