"""06 — Error mitigation: M3 / readout EM

[doc-require: ]
[doc-output-include: stdout, source]

读取误差是芯片上最便宜的可纠错部分。``ReadoutEM`` 自动从
``~/.uniqc/calibration_cache/`` 读 readout 校准结果，对 counts 做线性反演修正
（M3 在多比特上是更紧凑的 LSQR 实现）。
"""

from __future__ import annotations

import tempfile

from uniqc import Circuit
from uniqc.backend_adapter.task.adapters import DummyAdapter
from uniqc.calibration.readout import ReadoutCalibrator
from uniqc.qem import ReadoutEM


def main() -> None:
    cache_dir = tempfile.mkdtemp(prefix="uniqc-qem-")
    adapter = DummyAdapter(noise_model={"readout": [0.07, 0.10]})

    ReadoutCalibrator(adapter=adapter, shots=200, cache_dir=cache_dir).calibrate_1q(0)

    circuit = Circuit(1)
    circuit.x(0)
    circuit.measure(0)
    task_id = adapter.submit(circuit.originir, shots=400)
    raw = adapter.query(task_id)["result"]
    observed = {int(k, 2): v for k, v in raw.items()}

    mitigator = ReadoutEM(adapter=adapter, shots=200, cache_dir=cache_dir)
    corrected = mitigator.mitigate_counts(observed, measured_qubits=[0])

    print("observed:       ", observed)
    print("mitigated (~):  ", {k: round(v, 2) for k, v in corrected.items()})


if __name__ == "__main__":
    main()
