(platforms-ibm)=
# IBM Quantum

## 简介

uniqc 通过 `QiskitAdapter` 接入 IBM Quantum：线路按
OriginIR → QASM → `qiskit.QuantumCircuit` 转换，经
`qiskit-ibm-runtime` 提交。

## 安装

qiskit 是 unified-quantum 的核心依赖，默认安装即可，无需额外 extra。

## 配置凭证

```bash
uniqc config set ibm.token <YOUR_IBM_TOKEN>
```

如需代理：

```bash
uniqc config set ibm.proxy.http http://proxy:8080
uniqc config set ibm.proxy.https https://proxy:8080
```

## 查看后端

```bash
uniqc backend list -p ibm
```

可用模拟器如 `ibm_qasm_simulator`，真机后端名随设备代数变化
（如 `ibm_brisbane`、`ibm_fez`）。

## 提交任务

```bash
uniqc submit circuit.ir --backend ibm:ibm_qasm_simulator --shots 1000 --wait
```

Python：

```python
from uniqc import Circuit, submit_task, wait_for_result

c = Circuit()
c.h(0)
c.cnot(0, 1)
c.measure(0)
c.measure(1)

task_id = submit_task(c, backend="ibm:ibm_qasm_simulator", shots=1000)
print(wait_for_result(task_id))
```

## 平台约定与限制

- 输入类型为 `qiskit.QuantumCircuit`，转换由 `IBMCircuitAdapter` 自动完成，
  支持所有标准 OpenQASM 2.0 门。
- `submit()` 为**同步**（提交即阻塞等待），`submit_batch()` 在一个 Job 内
  批量执行。
- 提交前校验按后端 `basis_gates` 元数据进行，支持 `auto_mapping` 与
  `circuit_optimize` 选项。
- 结果为扁平 `{bitstring: shots}` counts（batch 查询返回列表），bitstring
  序遵循
  {ref}`统一 endianness 约定 <platform-bit-endianness>`——
  IBM 原生 BitArray 顺序已被 normalizer 改写。
