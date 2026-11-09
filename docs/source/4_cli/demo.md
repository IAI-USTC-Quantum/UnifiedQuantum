# demo — 本地量子实验

`uniqc demo` 与浏览器 Local quantum lab 使用相同入口，通过既有原生模拟器
展示 GHZ、W 态和 Ramsey 干涉的精确概率。

```bash
uniqc demo --help
uniqc demo --case ghz --qubits 4 --output ghz.json
uniqc demo --case w --qubits 3
uniqc demo --case ramsey --qubits 3 --phase 0.73
```

`--case` 为 `ghz`、`w` 或 `ramsey`，`--qubits` 为 2–8 的整数。
`--phase` 为弧度，范围为 `[-2π, 2π]`，仅 Ramsey 使用。
指定 `--output` 时将 JSON 写入该文件，否则输出到标准输出。

结果包括实际 OriginIR、概率、概率之和、独立解析最大误差和本机运行时间。
位串右侧对应 `q[0]`；这里的时间是本地软件运行时间，概率由 statevector
精确计算，不是 shots 采样频率。

[浏览器界面与安装说明](../5_webui/index.md)
