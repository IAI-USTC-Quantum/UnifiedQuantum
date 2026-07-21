"""06 — 云后端提交模板与 dry-run

[doc-require: ]
[doc-output-include: stdout, source]

展示真实后端路径的安全模板：先 ``dry_run_task``，再提交。该例子默认仅执行 dummy
dry-run；真实 OriginQ / QuarkStudio / IBM 提交单元应在维护者确认 token、账号额度和后端
可用后再打开（参考 ``[doc-require: originq]`` 等门控）。
"""

from __future__ import annotations

from uniqc import Circuit, dry_run_task


def main() -> None:
    circuit = Circuit()
    circuit.h(0)
    circuit.measure(0)

    result = dry_run_task(circuit, backend="dummy:local:simulator", shots=100)
    print("dummy dry-run success:", result.success)
    print("details:", result.details)

    cloud_templates = {
        "originq API": "submit_task(circuit, backend='originq:PQPUMESH8', shots=1000)",
        "quark API": "submit_task(circuit, backend='quark:Baihua', shots=1000)",
        "ibm API": "submit_task(circuit, backend='ibm:ibm_fez', shots=1000)",
        "CLI dry-run": "uniqc submit bell.originir --backend originq:PQPUMESH8 --dry-run",
    }
    for name, snippet in cloud_templates.items():
        print(f"{name}: {snippet}")


if __name__ == "__main__":
    main()
