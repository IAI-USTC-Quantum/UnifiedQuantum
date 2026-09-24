# UnifiedQuantum Examples

> 示例代码对应 [文档中心](https://iai-ustc-quantum.github.io/UnifiedQuantum/docs/) 中的快速开始、基础用法、进阶专题和最佳实践章节。

## 示例代码目录

| 目录 | 说明 |
|------|------|
| [0_quickstart/](0_quickstart/) | [一文上手](https://iai-ustc-quantum.github.io/UnifiedQuantum/docs/source/0_quickstart/index.html)：本地模拟 + dummy 提交 + 真机模板（`01_quickstart.py`） |
| [1_basic_usage/](1_basic_usage/) | 基础 API：[电路构建](https://iai-ustc-quantum.github.io/UnifiedQuantum/docs/source/1_basic_usage/circuit.html)、[本地模拟](https://iai-ustc-quantum.github.io/UnifiedQuantum/docs/source/1_basic_usage/simulation.html)、[提交与后处理](https://iai-ustc-quantum.github.io/UnifiedQuantum/docs/source/1_basic_usage/submit_task.html)、配置、可视化 |
| [2_advanced/](2_advanced/) | 进阶专题：编译选项、Region 选择器、变分 QAOA、dummy 含噪、[XEB 标定](https://iai-ustc-quantum.github.io/UnifiedQuantum/docs/source/2_advanced/calibration.html)、QEM-M3、[MPS 模拟器](https://iai-ustc-quantum.github.io/UnifiedQuantum/docs/source/2_advanced/mps_simulator.html)，以及 `algorithms/` `circuits/` `measurement/` `state_preparation/` `wk180/` 五个分类子目录 |
| [3_best_practices/](3_best_practices/) | 发布前可验证路径检查脚本（11 个 `XX_*.py`，配合 `scripts/build_docs.py` 使用） |
| [4_cli/](4_cli/) | [CLI 走查](https://iai-ustc-quantum.github.io/UnifiedQuantum/docs/source/4_cli/index.html)（`01_cli_walkthrough.py`）与 `cli_example/` 详细配方 |
| [5_webui/](5_webui/) | Gateway / WebUI 演示（`01_gateway_demo.py`） |

## 快速导航

**新手入门**

```bash
python examples/0_quickstart/01_quickstart.py
python examples/1_basic_usage/01_circuit_basics.py
python examples/1_basic_usage/04_config.py
```

**算法示例**

```bash
python examples/2_advanced/algorithms/grover.py --n-qubits 3
python examples/2_advanced/03_variational_qaoa.py
```

**进阶功能**

```bash
python examples/2_advanced/07_mps_simulator.py
python examples/2_advanced/06_qem_m3.py
```
