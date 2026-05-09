"""01 — Circuit basics: gates, qregs, OriginIR / OpenQASM export

[doc-require: ]
[doc-output-include: stdout, source]

最常用的 ``Circuit`` 能力：原生 gate API、寄存器、测量，以及导出到 OriginIR /
OpenQASM 2.0 两种文本格式。
"""

from __future__ import annotations

import math

from uniqc import Circuit


def main() -> None:
    c = Circuit()
    c.h(0)
    c.x(1)
    c.rx(2, math.pi / 2)
    c.cnot(0, 1)
    c.cz(1, 2)
    c.measure(0, 1, 2)

    print("== OriginIR ==")
    print(c.originir)

    print("== OpenQASM 2.0 ==")
    print(c.qasm)

    print("== qubit remapping ==")
    remapped = c.remapping({0: 100, 1: 101, 2: 102})
    print(remapped.originir)


if __name__ == "__main__":
    main()
