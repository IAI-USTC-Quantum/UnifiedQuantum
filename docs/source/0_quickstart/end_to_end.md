# 端到端验证

下面这个例子把"构造线路 → 本地模拟 → 通过 ``submit_task`` 在 dummy 上跑一遍 → 真机
提交模板"四件事一次走完。如果你的 ``unified-quantum`` 装好了，运行它应该不报错。

## 示例

```{include} ../_generated/examples/0_quickstart/01_quickstart.md
```

## 真机提交一行版

```python
from uniqc import Circuit, submit_task, wait_for_result

c = Circuit(); c.h(0); c.cnot(0, 1); c.measure(0, 1)
task_id = submit_task(c, backend="originq:WK_C180", shots=1000)
print(wait_for_result(task_id))
```

或 CLI：

```bash
uniqc submit circuit.ir --backend originq:WK_C180 --shots 1000 --wait
```

## 验证环境

安装与配置完成后，可运行 `uniqc doctor` 一键验证环境（依赖、配置、缓存、网络连通性等），
详见 [`uniqc doctor`](../4_cli/doctor.md)。

## 下一步

* [基本用法](../1_basic_usage/index.md)：常用 API、配置、可视化、后处理。
* [进阶教程](../2_advanced/index.md)：编译选项、区域选择、变分算法、calibration、QEM、MPS。
* [最佳实践](../3_best_practices/index.md)：发布前可重跑的 11 个完整场景。
* [CLI 介绍](../4_cli/index.md) / [WebUI](../5_webui/index.md) / [API 参考](../6_api/index.md)。
