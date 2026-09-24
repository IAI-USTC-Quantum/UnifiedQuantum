# UnifiedQuantum Circuit Examples

基于 `uniqc` 根导出的算法组件示例代码。

## 示例列表

- [qft.py](qft.py) — 量子傅里叶变换
- [deutsch-jozsa.py](deutsch-jozsa.py) — Deutsch-Jozsa 算法
- [thermal_state.py](thermal_state.py) — 热态制备
- [dicke_state.py](dicke_state.py) — Dicke 态制备
- [grover_oracle.py](grover_oracle.py) — Grover Oracle 构造
- [vqd.py](vqd.py) — 变分量子 deflate（激发态搜索）
- [amplitude_estimation.py](amplitude_estimation.py) — 量子振幅估计
- [entangled_states.py](entangled_states.py) — GHZ / W / Cluster 纠缠态

## 运行方式

从仓库根目录执行：

```bash
python examples/circuits/qft.py --n-qubits 3 --input-state 5
```
