"""04 — Dummy chip noise: ``dummy:<platform>:<backend>``

[doc-require: ]
[doc-output-include: stdout, source]

``dummy:<platform>:<backend>`` 是规则型 backend id：**它不会出现在 backend 列表**，
但提交时会先按真实 backend compile/transpile，然后用本地 dummy adapter 注入对应芯片
的标定噪声。常用形态：

* ``dummy:local:simulator`` — 完全无约束、无噪声；
* ``dummy:local:virtual-line-N`` / ``virtual-grid-RxC`` — 虚拟拓扑、无噪声；
* ``dummy:local:mps-linear-N[:chi=K[:cutoff=E]]`` — 线性 MPS 引擎；
* ``dummy:<platform>:<backend>`` — 真芯片拓扑 + 标定噪声（需要芯片缓存）。

最后一种需要先用 ``uniqc backend update --platform originq`` 等命令把芯片缓存
拉下来；本例只演示三种 ``dummy:local:*`` 形态。
"""

from __future__ import annotations

from uniqc import Circuit
from uniqc.backend_adapter.dummy_backend import resolve_dummy_backend
from uniqc.backend_adapter.task_manager import submit_task, wait_for_result


def main() -> None:
    circuit = Circuit(3)
    circuit.h(0)
    circuit.cnot(0, 1)
    circuit.cnot(1, 2)
    circuit.measure(0, 1, 2)

    for backend in (
        "dummy:local:simulator",
        "dummy:local:virtual-line-3",
        "dummy:local:mps-linear-3:chi=8",
    ):
        spec = resolve_dummy_backend(backend)
        print(f"== {backend} ==")
        print("  description:    ", spec.description)
        print("  topology:       ", spec.available_topology)
        print("  simulator_kwargs:", spec.simulator_kwargs)
        task = submit_task(circuit, backend=backend, shots=256)
        result = wait_for_result(task, timeout=30)
        print("  counts:         ", result)


if __name__ == "__main__":
    main()
