# 线路绘制 (`uniqc draw`)

把 OriginIR / OpenQASM 2.0 电路文件渲染成字符画、矢量图、位图、quantikz 源码或
自包含 HTML。渲染内核与 Python API `Circuit.draw()` 完全一致（见
[构造电路 · 可视化](circuit-visualization)）。

## 基本用法

```bash
# 字符画（默认，纯 ASCII 输出到终端）
uniqc draw bell.originir

# Unicode 符号集（● ⊕ × ┤ ├）
uniqc draw bell.originir --unicode

# 矢量图 / 位图 / quantikz 源码 / HTML
uniqc draw bell.originir -m svg  -o bell.svg
uniqc draw bell.originir -m png  -o bell.png
uniqc draw bell.originir -m latex
uniqc draw bell.originir -m interactive -o bell.html
```

## 选项

| 选项 | 取值 | 默认 |
|------|------|------|
| `--mode, -m` | `text` / `svg` / `png` / `mpl` / `latex` / `html` / `interactive` | `text` |
| `--style, -s` | `quantikz` / `qiskit` / `modern` / `print` | `quantikz` |
| `--fold` | `auto` / 整数 / `0`（不折叠） | `auto` |
| `--orientation` | `h`（时间→）/ `v`（时间↓） | `h` |
| `--theme` | `light` / `dark` | `light` |
| `--param-mode` | `pi` / `decimal` / `symbol` / `hidden` | `pi` |
| `--show-clbits` | 画经典双线 | 关 |
| `--unicode, -u` | Unicode 字符画符号集 | 关（纯 ASCII） |
| `--output, -o` | 输出文件 | stdout（`png` 必须给 `-o`） |

`fold=auto` 时，字符画按当前终端宽度折叠换行；图形模式按 16 门/行折叠。
