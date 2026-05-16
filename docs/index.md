# UnifiedQuantum

```{image} https://raw.githubusercontent.com/IAI-USTC-Quantum/UnifiedQuantum/v0.0.5/banner_uniqc.png
:alt: UnifiedQuantum
:width: 100%
```

**UnifiedQuantum**（``unified-quantum``，CLI ``uniqc``）—— 一个统一、非商业的
量子计算聚合框架。它给跨平台量子线路构建、模拟、云端执行提供**单一接口**，并且
在此之上提供完整的**芯片标定 + 量子误差缓解（QEM）工具集**。

* **多平台聚合**：OriginQ、IBM Quantum、Quark，加上本地 ``dummy`` 模拟器，
  共享 ``submit_task`` / ``uniqc submit`` 同一接口。
* **CLI-first**：``uv tool install unified-quantum`` 后全局可用 ``uniqc``，覆盖
  线路构建、本地模拟、提交、查询、配置、calibration 全流程。
* **AI 友好**：每个 ``--help`` 输出都附带文档链接、Rich 面板引导，以及
  ``--ai-hints`` 选项给 AI 工作流。
* **可复现**：所有示例代码（``examples/<chapter>/*.py``）都会被文档构建器重跑，
  输出直接拼进文档；只要本地能 ``make html``，示例就一定是可运行的。

## 一段最短的代码

```python
from uniqc import Circuit, submit_task, wait_for_result

c = Circuit()
c.h(0)
c.cnot(0, 1)
c.measure(0, 1)

task_id = submit_task(c, backend="dummy:local:simulator", shots=1024)
print(wait_for_result(task_id))
```

或 CLI：

```bash
uniqc simulate circuit.ir --shots 1000
uniqc submit circuit.ir --backend originq:WK_C180 --shots 1000 --wait
```

## 章节导航

```{toctree}
:maxdepth: 2
:caption: 文档

source/0_quickstart/index
source/1_basic_usage/index
source/2_advanced/index
source/3_best_practices/index
source/4_cli/index
source/5_webui/index
source/6_api/index
source/7_releases/index
```

## 关于

* GitHub: <https://github.com/IAI-USTC-Quantum/UnifiedQuantum>
* PyPI: <https://pypi.org/project/unified-quantum/>
* 维护团队: [Institute of Artificial Intelligence, Hefei Comprehensive National Science Center](https://iai-ustc-quantum.github.io/)
* 联系: chenzhaoyun@iai.ustc.edu.cn

🚧 在持续开发中，API 可能变化。
