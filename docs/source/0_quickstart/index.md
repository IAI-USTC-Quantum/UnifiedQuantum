# Quickstart

第一次接触 UnifiedQuantum？这一章从**安装 → 本地模拟 → 真机提交**走一遍最短路径，
帮你确认环境是可用的。

## 1. 安装

推荐用 [uv](https://github.com/astral-sh/uv)：

```bash
# 全局安装 CLI（不依赖任何虚拟环境）
uv tool install unified-quantum

# 同时安装 Python API（可与 CLI 共存）
uv pip install unified-quantum
```

也可以用 pip：

```bash
pip install unified-quantum
```

## 2. 配置真机平台（推荐 OriginQ）

```bash
uniqc config init
uniqc config set originq.token <YOUR_ORIGINQ_TOKEN>
uniqc config validate
```

* OriginQ 是目前推荐的入门平台：免费试用门槛低、文档完整、`uniqc backend list -p originq`
  能看到全部芯片。
* 其它平台同理：`uniqc config set quafu.token ...` / `uniqc config set ibm.token ...` /
  `uniqc config set quark.token ...`。

## 3. 端到端验证

下面这个例子把"构造线路 → 本地模拟 → 通过 ``submit_task`` 在 dummy 上跑一遍 → 真机
提交模板"四件事一次走完。如果你的 ``unified-quantum`` 装好了，运行它应该不报错。

```{include} ../_generated/examples/0_quickstart/01_quickstart.md
```

## 4. 真机提交一行版

```python
from uniqc import Circuit, submit_task, wait_for_result

c = Circuit(); c.h(0); c.cnot(0, 1); c.measure(0, 1)
task_id = submit_task(c, backend="originq", shots=1000, backend_name="WK_C180")
print(wait_for_result(task_id))
```

或 CLI：

```bash
uniqc submit circuit.ir -p originq -b WK_C180 -s 1000 --wait
```

## 下一步

* [基本用法](../1_basic_usage/index.md)：常用 API、配置、可视化、后处理。
* [进阶教程](../2_advanced/index.md)：编译选项、区域选择、变分算法、calibration、QEM、MPS。
* [最佳实践](../3_best_practices/index.md)：发布前可重跑的 11 个完整场景。
* [CLI 介绍](../4_cli/index.md) / [WebUI](../5_webui/index.md) / [API 参考](../6_api/index.md)。
