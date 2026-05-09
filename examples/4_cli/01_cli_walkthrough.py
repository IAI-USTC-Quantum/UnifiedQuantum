"""01 — CLI walkthrough: all the ``uniqc`` subcommands

[doc-require: ]
[doc-output-include: stdout, source]

把所有常用 CLI 子命令通过 ``subprocess.run`` 拉一遍，方便你看到每个命令的实际输出
形态。覆盖：

* ``uniqc --help``
* ``uniqc backend list``
* ``uniqc simulate <file>``
* ``uniqc submit <file> -p dummy --wait``
* ``uniqc result <task_id>``
* ``uniqc task list``

需要真实 token 的子命令（``uniqc config set originq.token ...``、``uniqc submit -p originq``、
``uniqc calibrate xeb``）只演示帮助文本，不会真的提交。
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _run(args: list[str]) -> str:
    result = subprocess.run(
        [sys.executable, "-m", "uniqc.cli", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout or result.stderr


def main() -> None:
    print("== uniqc --help ==")
    print(_run(["--help"]))

    print("== uniqc backend list (dummy only; cloud backends require credentials) ==")
    print(_run(["backend", "list", "--platform", "dummy"]))

    workdir = pathlib.Path(tempfile.mkdtemp(prefix="uniqc-cli-walk-"))
    bell = workdir / "bell.originir"
    bell.write_text(
        "QINIT 2\nCREG 2\nH q[0]\nCNOT q[0], q[1]\n"
        "MEASURE q[0], c[0]\nMEASURE q[1], c[1]\n",
        encoding="utf-8",
    )

    print("== uniqc simulate bell.originir --shots 256 ==")
    print(_run(["simulate", str(bell), "--shots", "256"]))

    print("== uniqc submit bell.originir -p dummy -s 64 --wait --format json ==")
    out = _run(["submit", str(bell), "-p", "dummy", "-s", "64", "--wait", "--format", "json"])
    print(out)

    try:
        payload = json.loads(out)
        task_id = payload.get("task_id") or payload.get("id")
    except Exception:
        task_id = None

    if task_id:
        print(f"== uniqc result {task_id} ==")
        print(_run(["result", task_id]))

    print("== uniqc task list (most recent few) ==")
    print(_run(["task", "list", "--limit", "5"]))


if __name__ == "__main__":
    main()
