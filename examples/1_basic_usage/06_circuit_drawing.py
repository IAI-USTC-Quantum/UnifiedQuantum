"""06 — Draw circuits (text / svg / png / latex / html / interactive)

[doc-require: matplotlib]
[doc-output-include: stdout, figures, source]

``Circuit.draw()`` 是统一的线路绘制入口（等价于
``uniqc.visualization.render``）：

* ``"text"`` 自研字符画（不依赖 pyqpanda3，Python 3.14 可用；默认纯 ASCII，
  ``charset="unicode"`` 切换 Unicode 符号）；
* ``"svg"`` / ``"png"`` / ``"mpl"`` 矢量图、位图、matplotlib Figure；
* ``"latex"`` 生成 quantikz 源码；
* ``"html"`` / ``"interactive"`` 自包含 HTML（后者支持点击门查看详情）。

四种皮肤：``quantikz``（默认）/ ``qiskit`` / ``modern`` / ``print``；横纵方向、
每行门数折叠、明暗主题、参数显示模式等全部可调。
"""

from __future__ import annotations

import math

from uniqc import Circuit


def _demo_circuit() -> Circuit:
    c = Circuit(3)
    c.h(0)
    c.cnot(0, 1)
    c.cz(0, 2)
    c.rx(1, math.pi / 2)
    c.swap(1, 2)
    with c.dagger():
        c.t(2)
    c.measure(0, 1, 2)
    return c


def main() -> None:
    c = _demo_circuit()

    # 1) 字符画（终端默认；fold 显式给定以保持文档输出确定，默认 auto 按终端宽度）
    print("== text (ascii, 默认) ==")
    print(c.draw("text", fold=0))  # fold 显式给定：文档输出需与终端宽度无关
    print("== text (unicode, 显示经典线) ==")
    print(c.draw("text", charset="unicode", show_clbits=True, fold=0))

    # 2) SVG：四种皮肤 + 折叠换行；返回 SVG 字符串，可直接保存
    svg = c.draw("svg", style="quantikz", show_clbits=True)
    print("svg bytes:", len(svg))
    print("quantikz 学术风 / qiskit 经典风 / modern 现代风 / print 灰度风均可选；"
          "CNOT 以 ●（控制）→ ⊕（目标）表达，受控关系一目了然。")

    # 3) quantikz LaTeX 源码（可直接 \input 进论文）
    print("== latex（quantikz 源码节选）==")
    print("\n".join(c.draw("latex").splitlines()[:4]))

    # 4) matplotlib Figure（被文档构建捕获为图片；需要 visualization extra）
    fig = c.draw("mpl", show_clbits=True)
    fig.suptitle("uniqc Circuit.draw('mpl')")

    # 5) 位图 / HTML / 交互式（写入文件，浏览器打开）
    png = c.draw("png")
    print("png magic ok:", png[:4] == b"\x89PNG", "| bytes:", len(png) > 1000)
    html = c.draw("interactive", style="modern")
    print("interactive html bytes:", len(html) > 1000)


if __name__ == "__main__":
    main()
