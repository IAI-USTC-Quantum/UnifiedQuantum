#!/usr/bin/env python3
"""Generate executed best-practice notebooks for the documentation site.

The notebooks are intentionally small and deterministic.  They are not CI; they
are release-time walkthroughs that prove the user-facing paths still work.
"""

from __future__ import annotations

import base64
import contextlib
import io
import json
import os
import pathlib
import sys
import textwrap
import traceback
from dataclasses import dataclass
from typing import Any

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = PROJECT_ROOT / "docs" / "source" / "best_practices"


@dataclass(frozen=True)
class Cell:
    kind: str
    source: str


def md(source: str) -> Cell:
    return Cell("markdown", textwrap.dedent(source).strip() + "\n")


def code(source: str) -> Cell:
    return Cell("code", textwrap.dedent(source).strip() + "\n")


def _image_output(png: bytes) -> dict[str, Any]:
    return {
        "output_type": "display_data",
        "data": {"image/png": base64.b64encode(png).decode("ascii")},
        "metadata": {},
    }


def _stream_output(name: str, text: str) -> dict[str, Any]:
    return {"output_type": "stream", "name": name, "text": text}


def _error_output(exc: BaseException) -> dict[str, Any]:
    return {
        "output_type": "error",
        "ename": exc.__class__.__name__,
        "evalue": str(exc),
        "traceback": traceback.format_exception(exc),
    }


def _execute_notebook(cells: list[Cell]) -> dict[str, Any]:
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/uniqc-matplotlib")
    os.environ.setdefault("MPLBACKEND", "Agg")

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ns: dict[str, Any] = {
        "__name__": "__main__",
        "__file__": str(NOTEBOOK_DIR / "generated_notebook.py"),
        "PROJECT_ROOT": PROJECT_ROOT,
    }
    rendered: list[dict[str, Any]] = []
    execution_count = 1

    for cell in cells:
        cell_id = f"cell-{len(rendered) + 1:03d}"
        if cell.kind == "markdown":
            rendered.append(
                {
                    "cell_type": "markdown",
                    "id": cell_id,
                    "metadata": {},
                    "source": cell.source,
                }
            )
            continue

        stdout = io.StringIO()
        stderr = io.StringIO()
        outputs: list[dict[str, Any]] = []
        exc: BaseException | None = None

        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                exec(compile(cell.source, "<best-practice-notebook>", "exec"), ns)
            except BaseException as err:  # noqa: BLE001
                exc = err

        if stdout.getvalue():
            outputs.append(_stream_output("stdout", stdout.getvalue()))
        if stderr.getvalue():
            outputs.append(_stream_output("stderr", stderr.getvalue()))

        for fig_num in plt.get_fignums():
            fig = plt.figure(fig_num)
            png = io.BytesIO()
            fig.savefig(png, format="png", bbox_inches="tight", dpi=120)
            outputs.append(_image_output(png.getvalue()))
        plt.close("all")

        if exc is not None:
            outputs.append(_error_output(exc))

        rendered.append(
            {
                "cell_type": "code",
                "execution_count": execution_count,
                "id": cell_id,
                "metadata": {},
                "outputs": outputs,
                "source": cell.source,
            }
        )
        execution_count += 1

        if exc is not None:
            raise exc

    return {
        "cells": rendered,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "pygments_lexer": "ipython3",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def _write_notebook(filename: str, cells: list[Cell]) -> None:
    NOTEBOOK_DIR.mkdir(parents=True, exist_ok=True)
    notebook = _execute_notebook(cells)
    path = NOTEBOOK_DIR / filename
    path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {path.relative_to(PROJECT_ROOT)}")


COMMON_IMPORTS = r"""
import math
import pathlib
import tempfile

import matplotlib.pyplot as plt
import numpy as np

from uniqc import Circuit
from uniqc.simulator import OriginIR_Simulator


def probability_dict(values):
    if isinstance(values, dict):
        total = sum(values.values()) or 1
        return {format(int(k), "b") if isinstance(k, int) else str(k): v / total for k, v in values.items()}
    n = int(math.log2(len(values))) if values else 0
    return {format(i, f"0{n}b"): float(p) for i, p in enumerate(values) if abs(float(p)) > 1e-12}


def plot_probs(probs, title):
    labels = list(probs)
    values = [probs[k] for k in labels]
    fig, ax = plt.subplots(figsize=(6, 3.4))
    ax.bar(labels, values, color="#3267a8")
    ax.set_ylim(0, max(1.0, max(values, default=0) * 1.2))
    ax.set_xlabel("bitstring")
    ax.set_ylabel("probability")
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
"""


NOTEBOOKS: dict[str, list[Cell]] = {
    "00_config_and_backend_cache.ipynb": [
        md(
            """
            # 00. 配置 Key 与后端缓存

            这个案例验证最早的用户路径：创建配置、写入平台 token、校验配置结构，并用本地构造的
            `BackendInfo` 演示后端缓存的写入、读取和审查。真实 token 不会写入文档输出。
            """
        ),
        code(
            """
            import tempfile
            from pathlib import Path

            from uniqc.backend_adapter.config import load_config, save_config, validate_config
            from uniqc.backend_adapter.backend_cache import cache_info, get_cached_backends, update_cache
            from uniqc import BackendInfo, Platform, QubitTopology, audit_backends

            workdir = Path(tempfile.mkdtemp(prefix="uniqc-bp-config-"))
            config_path = workdir / "config.yaml"

            config = {
                "active_profile": "release-check",
                "release-check": {
                    "originq": {"token": "originq-token-redacted"},
                    "quafu": {"token": "quafu-token-redacted"},
                    "ibm": {"token": "ibm-token-redacted", "proxy": {"http": "", "https": ""}},
                },
            }
            save_config(config, config_path=config_path)

            loaded = load_config(config_path=config_path)
            errors = validate_config(config_path=config_path)
            print("profile:", loaded["active_profile"])
            print("validation errors:", errors)

            backend = BackendInfo(
                platform=Platform.DUMMY,
                name="virtual-line-3",
                description="release-check virtual backend",
                num_qubits=3,
                topology=(QubitTopology(0, 1), QubitTopology(1, 2)),
                status="available",
                is_simulator=True,
            )
            update_cache(Platform.DUMMY, [backend], cache_dir=workdir)
            cached = get_cached_backends(Platform.DUMMY, cache_dir=workdir)
            print("cached backend ids:", [b.full_id() for b in cached])
            print("cache platforms:", sorted(cache_info(cache_dir=workdir)))
            print("audit issues:", audit_backends(cached))
            """
        ),
    ],
    "01_bare_circuit_simulation.ipynb": [
        md(
            """
            # 01. 裸 Circuit、本地模拟与结果可视化

            从空 `Circuit` 构造 Bell 态，导出 OriginIR / OpenQASM 2.0，使用本地模拟器得到概率分布并画图。
            """
        ),
        code(COMMON_IMPORTS),
        code(
            """
            circuit = Circuit()
            circuit.h(0)
            circuit.cnot(0, 1)
            circuit.measure(0, 1)

            print("OriginIR:")
            print(circuit.originir)
            print("QASM header:")
            print("\\n".join(circuit.qasm.splitlines()[:6]))

            sim = OriginIR_Simulator()
            probs = probability_dict(sim.simulate_pmeasure(circuit.originir))
            print("probabilities:", probs)
            plot_probs(probs, "Bell state probabilities")
            """
        ),
    ],
    "02_named_circuit_and_reuse.ipynb": [
        md(
            """
            # 02. Named Circuit 与可复用线路

            用命名寄存器和 `@circuit_def` 组织可复用子线路，再组合成一个 4-qubit GHZ-like 电路。
            """
        ),
        code(COMMON_IMPORTS),
        code(
            """
            from uniqc import circuit_def

            @circuit_def(name="bell_pair", qregs={"q": 2})
            def bell_pair(circ, q):
                circ.h(q[0])
                circ.cnot(q[0], q[1])
                return circ

            @circuit_def(name="rz_layer", qregs={"q": 4}, params=["angle"])
            def rz_layer(circ, q, angle):
                for i in range(4):
                    circ.rz(q[i], angle)
                return circ

            circuit = Circuit(qregs={"data": 4})
            data = circuit.get_qreg("data")

            bell_pair(circuit, qreg_mapping={"q": [data[0], data[1]]})
            bell_pair(circuit, qreg_mapping={"q": [data[2], data[3]]})
            circuit.cnot(data[1], data[2])
            rz_layer(circuit, qreg_mapping={"q": [data[0], data[1], data[2], data[3]]}, param_values={"angle": 0.25})
            circuit.measure(0, 1, 2, 3)

            print("DEF export:")
            print(bell_pair.to_originir_def())
            print("operations:", len(circuit.opcode_list))

            probs = probability_dict(OriginIR_Simulator().simulate_pmeasure(circuit.originir))
            print("non-zero states:", probs)
            plot_probs(probs, "Named circuit result")
            """
        ),
    ],
    "03_compile_region_dummy_backend.ipynb": [
        md(
            """
            # 03. 编译、拓扑与虚拟后端

            构造一个虚拟线性拓扑后端，把不满足相邻拓扑的线路编译到目标基门集合，并检查编译产物。
            """
        ),
        code(
            """
            from uniqc import BackendInfo, Circuit, Platform, QubitTopology, compile

            circuit = Circuit()
            circuit.h(0)
            circuit.cnot(0, 2)

            backend = BackendInfo(
                platform=Platform.DUMMY,
                name="virtual-line-3",
                num_qubits=3,
                topology=(QubitTopology(0, 1), QubitTopology(1, 2)),
                status="available",
                is_simulator=True,
            )

            compiled_originir = compile(circuit, backend_info=backend, output_format="originir")
            compiled_qasm = compile(circuit, backend_info=backend, output_format="qasm")

            print("backend:", backend.full_id())
            print("compiled OriginIR:")
            print(compiled_originir)
            print("compiled QASM first lines:")
            print("\\n".join(compiled_qasm.splitlines()[:8]))
            """
        ),
    ],
    "04_api_submit_dummy_result.ipynb": [
        md(
            """
            # 04. Python API 提交、取回与可视化

            使用 `submit_task(backend="dummy")` 验证远端任务接口的本地替代路径：提交、等待、查询缓存、画图。`backend="dummy"` 表示无约束、无噪声；需要虚拟拓扑时使用 `dummy:virtual-line-N` / `dummy:virtual-grid-RxC`，需要真实芯片噪声时使用 `dummy:<platform>:<backend>`。
            """
        ),
        code(COMMON_IMPORTS),
        code(
            """
            from uniqc import get_task, submit_task, wait_for_result

            circuit = Circuit()
            circuit.h(0)
            circuit.cnot(0, 1)
            circuit.measure(0, 1)

            task_id = submit_task(circuit, backend="dummy", shots=128, metadata={"example": "best-practices-api"})
            counts = wait_for_result(task_id)
            task = get_task(task_id)

            print("task_id:", task_id)
            print("status:", task.status)
            print("counts:", counts)

            probs = {k: v / sum(counts.values()) for k, v in counts.items()}
            plot_probs(probs, "API dummy submission result")
            """
        ),
    ],
    "05_cli_workflow_dummy.ipynb": [
        md(
            """
            # 05. CLI 提交完整链路

            Notebook 里通过 `subprocess.run` 执行 CLI：写出 OriginIR 文件，`uniqc submit --platform dummy --wait`，
            并展示返回结果。`--platform dummy` 默认对应无约束、无噪声的 `dummy`；可通过 `--backend virtual-line-3` 指定虚拟拓扑，或通过 `--backend originq:WK_C180` 走真实 backend compile/transpile + 本地含噪执行。真实发布检查时也可以把平台切换成云后端。
            """
        ),
        code(
            """
            import json
            import subprocess
            import sys
            import tempfile
            from pathlib import Path

            workdir = Path(tempfile.mkdtemp(prefix="uniqc-bp-cli-"))
            circuit_file = workdir / "bell.originir"
            circuit_file.write_text(
                "QINIT 2\\nCREG 2\\nH q[0]\\nCNOT q[0], q[1]\\nMEASURE q[0], c[0]\\nMEASURE q[1], c[1]\\n",
                encoding="utf-8",
            )

            cmd = [
                sys.executable,
                "-m",
                "uniqc.cli",
                "submit",
                str(circuit_file),
                "-p",
                "dummy",
                "-s",
                "64",
                "--wait",
                "--format",
                "json",
            ]
            completed = subprocess.run(cmd, cwd=PROJECT_ROOT, text=True, capture_output=True, check=True)
            print("command:", " ".join(cmd))
            print(completed.stdout)
            """
        ),
    ],
    "06_cloud_backend_template.ipynb": [
        md(
            """
            # 06. 云后端提交模板与 dry-run

            该案例展示真实后端路径的安全模板：先 dry-run，再提交。默认执行 dummy dry-run；
            真实 OriginQ / Quafu / IBM 提交单元应在维护者确认 token、账号额度和后端可用后再打开。
            """
        ),
        code(
            """
            from uniqc import Circuit, dry_run_task

            circuit = Circuit()
            circuit.h(0)
            circuit.measure(0)

            result = dry_run_task(circuit, backend="dummy", shots=100)
            print("dummy dry-run success:", result.success)
            print("details:", result.details)

            cloud_templates = {
                "originq API": "submit_task(circuit, backend='originq', shots=1000, backend_name='PQPUMESH8')",
                "quafu API": "submit_task(circuit, backend='quafu', shots=1000, chip_id='ScQ-P18')",
                "ibm API": "submit_task(circuit, backend='ibm', shots=1000, chip_id='ibm_fez')",
                "CLI dry-run": "uniqc submit bell.originir -p quafu -b ScQ-P18 --dry-run",
            }
            for name, snippet in cloud_templates.items():
                print(f"{name}: {snippet}")
            """
        ),
    ],
    "07_variational_circuit.ipynb": [
        md(
            """
            # 07. 简单变分量子线路

            用一个单参数 ansatz 最小化 `<Z>`。该例子故意不用外部优化库，便于确认线路、模拟和可视化路径。
            """
        ),
        code(COMMON_IMPORTS),
        code(
            """
            def build_ansatz(theta):
                c = Circuit()
                c.ry(0, float(theta))
                c.measure(0)
                return c

            def z_expectation(theta):
                counts = OriginIR_Simulator().simulate_shots(build_ansatz(theta).originir, shots=400)
                total = sum(counts.values()) or 1
                p0 = counts.get(0, 0) / total
                p1 = counts.get(1, 0) / total
                return p0 - p1

            theta = 0.2
            history = []
            for step in range(18):
                value = z_expectation(theta)
                plus = z_expectation(theta + math.pi / 2)
                minus = z_expectation(theta - math.pi / 2)
                grad = 0.5 * (plus - minus)
                history.append((step, theta, value, grad))
                theta -= 0.25 * grad

            for row in history[::4]:
                print("step=%02d theta=%.3f <Z>=%.3f grad=%.3f" % row)
            print("final theta:", round(theta, 4))

            fig, ax = plt.subplots(figsize=(6, 3.4))
            ax.plot([r[0] for r in history], [r[2] for r in history], marker="o")
            ax.set_xlabel("step")
            ax.set_ylabel("<Z>")
            ax.set_title("Variational circuit optimization")
            ax.grid(alpha=0.25)
            fig.tight_layout()
            """
        ),
    ],
    "08_torch_quantum_training.ipynb": [
        md(
            """
            # 08. Torch 集成后的量子线路

            用 PyTorch 管理参数和优化器，量子期望值由 UnifiedQuantum 线路和模拟器计算，梯度使用 parameter-shift 写回。
            """
        ),
        code(
            """
            import math
            import matplotlib.pyplot as plt
            import torch

            from uniqc import Circuit
            from uniqc.simulator import OriginIR_Simulator

            torch.manual_seed(7)

            def circuit_for(theta):
                c = Circuit()
                c.ry(0, float(theta))
                c.measure(0)
                return c

            def z_expectation(theta):
                counts = OriginIR_Simulator().simulate_shots(circuit_for(theta).originir, shots=400)
                total = sum(counts.values()) or 1
                return (counts.get(0, 0) - counts.get(1, 0)) / total

            theta = torch.nn.Parameter(torch.tensor(0.1))
            optimizer = torch.optim.SGD([theta], lr=0.3)
            history = []

            for step in range(16):
                optimizer.zero_grad()
                value = z_expectation(theta.item())
                grad = 0.5 * (
                    z_expectation(theta.item() + math.pi / 2)
                    - z_expectation(theta.item() - math.pi / 2)
                )
                theta.grad = torch.tensor(grad)
                optimizer.step()
                history.append((step, theta.item(), value, grad))

            print("torch parameter:", theta)
            print("last rows:", history[-3:])

            fig, ax = plt.subplots(figsize=(6, 3.4))
            ax.plot([r[0] for r in history], [r[2] for r in history], marker="o", label="<Z>")
            ax.plot([r[0] for r in history], [r[1] for r in history], marker="s", label="theta")
            ax.set_xlabel("step")
            ax.set_title("Torch optimizer with quantum expectation")
            ax.grid(alpha=0.25)
            ax.legend()
            fig.tight_layout()
            """
        ),
    ],
    "09_calibration_qem_dummy.ipynb": [
        md(
            """
            # 09. Calibration + QEM

            在带显式读出噪声的 dummy adapter 上运行读出校准，将校准结果写入临时缓存，再用 `ReadoutEM` 对同一个 noisy backend 产生的观测 counts 做修正。
            """
        ),
        code(
            """
            import tempfile
            import matplotlib.pyplot as plt

            from uniqc import Circuit
            from uniqc.backend_adapter.task.adapters import DummyAdapter
            from uniqc.calibration.readout import ReadoutCalibrator
            from uniqc.qem import ReadoutEM

            cache_dir = tempfile.mkdtemp(prefix="uniqc-bp-calibration-")
            adapter = DummyAdapter(noise_model={"readout": [0.08, 0.12]})
            calibrator = ReadoutCalibrator(adapter=adapter, shots=200, cache_dir=cache_dir)
            calibration = calibrator.calibrate_1q(0)

            observed_circuit = Circuit(1)
            observed_circuit.x(0)
            observed_circuit.measure(0)
            task_id = adapter.submit(observed_circuit.originir, shots=200)
            raw_counts = adapter.query(task_id)["result"]
            observed = {int(k, 2): v for k, v in raw_counts.items()}
            mitigator = ReadoutEM(adapter=adapter, shots=200, cache_dir=cache_dir)
            corrected = mitigator.mitigate_counts(observed, measured_qubits=[0])

            print("assignment fidelity:", round(calibration["assignment_fidelity"], 4))
            print("confusion matrix:", calibration["confusion_matrix"])
            print("observed:", observed)
            print("corrected:", {k: round(v, 2) for k, v in corrected.items()})

            labels = ["0", "1"]
            fig, ax = plt.subplots(figsize=(6, 3.4))
            x = range(len(labels))
            ax.bar([i - 0.18 for i in x], [observed[i] for i in x], width=0.36, label="observed")
            ax.bar([i + 0.18 for i in x], [corrected[i] for i in x], width=0.36, label="mitigated")
            ax.set_xticks(list(x))
            ax.set_xticklabels(labels)
            ax.set_ylabel("counts")
            ax.set_title("Readout error mitigation")
            ax.legend()
            ax.grid(axis="y", alpha=0.25)
            fig.tight_layout()
            """
        ),
    ],
    "10_xeb_workflow_dummy.ipynb": [
        md(
            """
            # 10. XEB workflow

            使用很小的参数运行 1q XEB，覆盖校准、ReadoutEM、随机线路生成、fidelity 拟合和结果图示。
            本 notebook 使用 `backend="dummy"` 搭配显式 `noise_model` 做本地含噪发布检查；如果要检查真实芯片标定噪声路径，应改用 `backend="dummy:originq:WK_C180"` 这类规则型 backend id，它会先按真实 backend compile/transpile，再本地含噪执行。
            发布前可以提高 `n_circuits` 和 `shots` 做更严格的人工检查。
            """
        ),
        code(
            """
            import tempfile
            import matplotlib.pyplot as plt

            from uniqc import xeb_workflow

            cache_dir = tempfile.mkdtemp(prefix="uniqc-bp-xeb-")
            results = xeb_workflow.run_1q_xeb_workflow(
                backend="dummy",
                qubits=[0],
                depths=[1, 2, 3],
                n_circuits=3,
                shots=128,
                use_readout_em=True,
                noise_model={"depol": 0.01, "readout": 0.04},
                seed=11,
                cache_dir=cache_dir,
            )

            result = results[0]
            print("fidelity_per_layer:", round(result.fidelity_per_layer, 6))
            print("fit parameters:", {"A": round(result.fit_a, 6), "B": round(result.fit_b, 6), "r": round(result.fit_r, 6)})
            print("depths:", result.depths)

            fitted = [result.fit_a * (result.fit_r ** depth) + result.fit_b for depth in result.depths]
            fig, ax = plt.subplots(figsize=(6, 3.4))
            ax.plot(result.depths, fitted, marker="o")
            ax.set_xlabel("depth")
            ax.set_ylabel("fitted fidelity")
            ax.set_title("1q XEB fitted release-check result")
            ax.grid(alpha=0.25)
            fig.tight_layout()
            """
        ),
    ],
}


INDEX = """# 最佳实践

最佳实践章节由一组已经执行过的 notebooks 组成。它们不是 CI，而是发布前的“可验证路径检查”：维护者通过重跑这些案例，确认用户从配置、构建线路、选择后端、提交任务、获取结果、可视化，到变分线路、Torch 集成、Calibration + QEM 的主路径仍然有效。

当前 dummy backend 的推荐写法是显式 backend id：`dummy` 表示无约束、无噪声；`dummy:virtual-line-N` / `dummy:virtual-grid-RxC` 表示带虚拟拓扑约束但无噪声；`dummy:<platform>:<backend>` 表示复用真实 backend 的拓扑和标定数据，先 compile/transpile，再本地含噪执行。最后一种是规则型写法，不会作为独立 backend 列表项展示。

## 覆盖矩阵

| 案例 | 配置 Key | 后端缓存 | 裸 Circuit | Named Circuit | 虚拟/本地后端 | API 提交 | CLI 提交 | 可视化 | 变分 | Torch | Calibration/QEM |
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

## 案例目录

```{toctree}
:maxdepth: 1

00_config_and_backend_cache
01_bare_circuit_simulation
02_named_circuit_and_reuse
03_compile_region_dummy_backend
04_api_submit_dummy_result
05_cli_workflow_dummy
06_cloud_backend_template
07_variational_circuit
08_torch_quantum_training
09_calibration_qem_dummy
10_xeb_workflow_dummy
```

## 发布前重跑

维护者发布前应在完整开发环境中重新生成这些 notebooks：

```bash
uv sync --all-extras --group dev --group docs --upgrade
uv run python scripts/generate_best_practice_notebooks.py
cd docs
uv run make html
```

如果某个案例因为真实云平台不可用而无法执行，应保持 dummy/dry-run 路径可执行，并在 Release note 中说明真实平台验证的缺口。
"""


def main() -> None:
    sys.path.insert(0, str(PROJECT_ROOT))
    os.chdir(PROJECT_ROOT)
    NOTEBOOK_DIR.mkdir(parents=True, exist_ok=True)
    (NOTEBOOK_DIR / "index.md").write_text(INDEX, encoding="utf-8")

    for filename, cells in NOTEBOOKS.items():
        _write_notebook(filename, cells)


if __name__ == "__main__":
    main()
