"""01 — Compile internals: levels, basis gates, virtual backends

[doc-require: ]
[doc-output-include: stdout, source]

``uniqc.compile.compile`` 把任意 ``Circuit`` 编译到目标后端的拓扑、基门集合和提交
语言。常用旋钮：

* ``backend_info`` — 目标后端（拓扑 + basis gates 的来源）；
* ``output_format="originir" | "qasm"`` — 提交语言；
* ``optimization_level=0..3`` — 编译激进度。

这里在两个虚拟后端上对比同一个跨距 CNOT 线路的编译产物。
"""

from __future__ import annotations

from uniqc import BackendInfo, Circuit, Platform, QubitTopology, compile


def make_backend(name: str, n: int, edges: list[tuple[int, int]]) -> BackendInfo:
    return BackendInfo(
        platform=Platform.DUMMY,
        name=name,
        num_qubits=n,
        topology=tuple(QubitTopology(u, v) for u, v in edges),
        status="available",
        is_simulator=True,
    )


def main() -> None:
    circuit = Circuit()
    circuit.h(0)
    circuit.cnot(0, 3)  # not nearest-neighbour
    circuit.measure(0, 3)

    line = make_backend("virtual-line-4", 4, [(0, 1), (1, 2), (2, 3)])
    grid = make_backend("virtual-grid-2x2", 4, [(0, 1), (1, 2), (2, 3), (0, 3)])

    for backend in (line, grid):
        print(f"== compile target: {backend.full_id()} ==")
        compiled = compile(circuit, backend_info=backend, output_format="originir")
        print(compiled)


if __name__ == "__main__":
    main()
