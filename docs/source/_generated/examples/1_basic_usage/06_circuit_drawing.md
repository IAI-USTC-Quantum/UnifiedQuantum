### 06 — Draw circuits (text / svg / png / latex / html / interactive)

*Source*: ``examples/1_basic_usage/06_circuit_drawing.py``  
*Status*: **pass**

``Circuit.draw()`` 是统一的线路绘制入口（等价于
``uniqc.visualization.render``）：

* ``"text"`` 自研字符画（不依赖 pyqpanda3，Python 3.14 可用；默认纯 ASCII，
  ``charset="unicode"`` 切换 Unicode 符号）；
* ``"svg"`` / ``"png"`` / ``"mpl"`` 矢量图、位图、matplotlib Figure；
* ``"latex"`` 生成 quantikz 源码；
* ``"html"`` / ``"interactive"`` 自包含 HTML（后者支持点击门查看详情）。

四种皮肤：``quantikz``（默认）/ ``qiskit`` / ``modern`` / ``print``；横纵方向、
每行门数折叠、明暗主题、参数显示模式等全部可调。

**Source code**

```{literalinclude} ../../../examples/1_basic_usage/06_circuit_drawing.py
:language: python
```

**Stdout**

```text
== text (ascii, 默认) ==
q[0] -|H|----*--------*-------|M|------------
q[1] -------(+)--|RX(pi/2)|----x-----|M|-----
q[2] -----------------*--------x----|T'|--|M|
== text (unicode, 显示经典线) ==
q[0] ─┤H├────●────────●───────┤M├────────────
q[1] ────────⊕────┤RX(π/2)├────×─────┤M├─────
q[2] ─────────────────●────────×────┤T†├──┤M├
                               ║      ║    ║
c[0] ═════════════════════════┤╪├═════║════║═
c[1] ════════════════════════════════┤╪├═══║═
c[2] ═════════════════════════════════════┤╪├
svg bytes: 6807
quantikz 学术风 / qiskit 经典风 / modern 现代风 / print 灰度风均可选；CNOT 以 ●（控制）→ ⊕（目标）表达，受控关系一目了然。
== latex（quantikz 源码节选）==
% MEASURE q[0] -> c[0] (classical wire omitted in quantikz)
% MEASURE q[1] -> c[1] (classical wire omitted in quantikz)
% MEASURE q[2] -> c[2] (classical wire omitted in quantikz)
\begin{quantikz}[column sep=0.9em, row sep=0.5em]
png magic ok: True | bytes: True
interactive html bytes: True
```

**Figures**

![06 — Draw circuits (text / svg / png / latex / html / interactive) — figure-01.svg](../_generated/examples/1_basic_usage/figures/06_circuit_drawing/figure-01.svg)

