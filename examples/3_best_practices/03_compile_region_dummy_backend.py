"""03 — 编译、拓扑与虚拟后端

[doc-require: ]
[doc-output-include: stdout, source]

构造一个虚拟线性拓扑后端，把不满足相邻拓扑的线路编译到目标基门集合，并检查编译产物。
"""

from __future__ import annotations

from uniqc import BackendInfo, Circuit, Platform, QubitTopology, compile


def main() -> None:
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
    print("\n".join(compiled_qasm.splitlines()[:8]))


if __name__ == "__main__":
    main()
