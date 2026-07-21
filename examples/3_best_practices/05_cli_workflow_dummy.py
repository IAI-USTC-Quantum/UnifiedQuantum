"""05 — CLI 提交完整链路

[doc-require: ]
[doc-output-include: stdout, source]

通过 ``subprocess.run`` 执行 CLI：写出 OriginIR 文件，``uniqc submit --backend dummy --wait``，
并展示返回结果。

* ``--backend dummy``（默认）对应无约束、无噪声的 ``dummy:local:simulator``；
* 可通过 ``--backend dummy:local:virtual-line-3`` 指定虚拟拓扑；
* 也可通过 ``--backend dummy:originq:WK_C180`` 走真实 backend compile/transpile + 本地含噪执行。
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]


def main() -> None:
    workdir = pathlib.Path(tempfile.mkdtemp(prefix="uniqc-bp-cli-"))
    circuit_file = workdir / "bell.originir"
    circuit_file.write_text(
        "QINIT 2\nCREG 2\nH q[0]\nCNOT q[0], q[1]\n"
        "MEASURE q[0], c[0]\nMEASURE q[1], c[1]\n",
        encoding="utf-8",
    )

    cmd = [
        sys.executable,
        "-m",
        "uniqc.cli",
        "submit",
        str(circuit_file),
        "--backend",
        "dummy",
        "-s",
        "64",
        "--wait",
        "--format",
        "json",
    ]
    completed = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    display_cmd = ["python", "-m", "uniqc.cli", "submit", "bell.originir", *cmd[5:]]
    print("command:", " ".join(display_cmd))
    print(completed.stdout)


if __name__ == "__main__":
    main()
