# MPS 模拟器 (MPSSimulator)

UnifiedQuantum 在原有的稠密态模拟器（`OriginIR_Simulator` / `OriginIR_NoisySimulator`，由 C++ 后端驱动）之外，新增了一个**纯 Python 的矩阵乘积态 (Matrix Product State, MPS) 模拟器**：[`uniqc.simulator.MPSSimulator`](#)。

它的目标场景是：

* **大量量子比特、纠缠适中**的电路（典型如一维链、Floquet/QSP/MPS 友好的 Trotter 电路、TFIM/海森堡演化等）
* 想要**避免装载 C++ 后端**（例如在 CI、容器或受限环境）
* 需要**精确无噪声**的参考结果，但 32 比特以上的稠密 statevector 已经放不下

支持的电路必须满足：

1. **开放边界一维链**——所有双比特门都作用在物理上相邻的量子比特对 `(i, i+1)` 上
2. **不含 `CONTROL...ENDCONTROL` 块或 `controlled_by(...)` 修饰**——MPS 引擎不支持任意控制门
3. **非噪声**——`MPSSimulator` 不接受 `noise_model` / `error_loader`

下表对比两类后端：

| 维度 | `OriginIR_Simulator` (C++) | `MPSSimulator` (Python) |
|---|---|---|
| 量子比特上限 | ~28（受内存限制） | 数百（取决于 χ） |
| 拓扑约束 | 任意 | **仅最近邻一维链** |
| 噪声模型 | ✅ Lindblad / 读出 | ❌ 仅理想电路 |
| 任意控制门 | ✅ | ❌ |
| 截断误差 | 无 | 由 `chi_max` / `svd_cutoff` 控制 |

## 直接调用 API

```python
from uniqc import Circuit
from uniqc.simulator import MPSSimulator, MPSConfig

c = Circuit(64)
c.h(0)
for i in range(63):
    c.cnot(i, i + 1)

sim = MPSSimulator(MPSConfig(chi_max=64, svd_cutoff=1e-12, seed=42))

# 大 N 必须用 simulate_shots：MPS 抽样 O(N · χ³) per shot
counts = sim.simulate_shots(c.originir, shots=1000)
print(counts)            # {0: ~500, 2**64-1: ~500}
print(sim.max_bond)      # = 2 for GHZ
print(sim.truncation_errors)  # 每次 SVD 截掉的奇异值平方和

# 小 N 可以拿稠密向量验证
psi = sim.simulate_statevector(c.originir)  # ≤ 24 qubit
probs = sim.simulate_pmeasure(c.originir)   # ≤ 24 measured qubit
```

`MPSConfig` 字段：

* `chi_max: int = 64` — 键维上限。χ 越大越精确，代价 `O(χ³)`；高度纠缠的线路需要把 `chi_max` 调大，单层张量的内存大致按 `N · χ² · d²` 增长（`d=2` 为单比特维度）
* `svd_cutoff: float = 1e-12` — 截掉小于该阈值的奇异值
* `seed: int | None = None` — `simulate_shots` 抽样的随机种子

## 通过 dummy 后端调用

跟 `dummy:virtual-line-N` 类似，MPS 模拟器作为一种 dummy 后端暴露给 `submit_task` / `wait_for_result` 流水线：

```python
from uniqc.backend_adapter.task_manager import submit_task, wait_for_result

task = submit_task(circuit, backend="dummy:mps:linear-32:chi=64:cutoff=1e-10", shots=500)
result = wait_for_result(task, timeout=60)
```

Backend identifier 语法：

```
dummy:mps:linear-<N>[:chi=<int>][:cutoff=<float>][:seed=<int>]
```

* `linear-N` 给出比特数与拓扑（`[[0,1],[1,2],...,[N-2,N-1]]`），dry-run 阶段会拒绝跨距 ≠ 1 的双比特门
* `chi`、`cutoff`、`seed` 三个 kwarg 会被转发到 `MPSConfig`
* 与 `dummy:virtual-line-N` 不同，MPS 后端**忽略噪声相关字段**；如果你想要噪声，请使用 `dummy:<platform>:<chip>` 或显式构造 `OriginIR_NoisySimulator`

## OriginIR 门集

遵循 uniqc OriginIR 解析器的命名约定（**不**接受 Qiskit 风格的 `RXX`/`RYY`/`RZZ`）：

| 类别 | 支持的门 |
|---|---|
| 1q 无参 | `H`, `X`, `Y`, `Z`, `S`, `T`, `SX`, `I` |
| 1q 参数 | `RX(θ)`, `RY(θ)`, `RZ(θ)`, `U1(θ)`, `U2(φ,λ)`, `U3(θ,φ,λ)`, `RPhi(θ,φ)`, `RPhi90(φ)`, `RPhi180(φ)` |
| 2q 无参 | `CNOT`, `CZ`, `SWAP`, `ISWAP`, `ECR` |
| 2q 参数 | `XX(θ)`, `YY(θ)`, `ZZ(θ)`, `XY(θ)`, `PHASE2Q(p1,p2,p3)` |

OriginIR 的参数语法是 `GATE q[a],q[b],(theta)`，**不是** `GATE(theta) q[a],q[b]`。

## 何时该选 MPS

| 电路 | 推荐后端 |
|---|---|
| ≤ 24 比特，任意拓扑，需要精确 | `OriginIR_Simulator` |
| 一维链，比特数大，纠缠浅 | `MPSSimulator` |
| 任意拓扑、需要噪声 | `dummy:<platform>:<chip>` 或真实硬件 |
| 跨距 > 1 的门 | 先用 SWAP 编译到最近邻，再走 MPS；或换 `OriginIR_Simulator` |

如果电路达到了体积律纠缠（例如随机量子电路深度 ≈ N），任何 χ 都会爆，此时 MPS 不是合适的工具。
