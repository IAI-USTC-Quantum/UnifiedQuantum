### 06 — 云后端提交模板与 dry-run

*Source*: ``examples/3_best_practices/06_cloud_backend_template.py``  
*Status*: **pass**

展示真实后端路径的安全模板：先 ``dry_run_task``，再提交。该例子默认仅执行 dummy
dry-run；真实 OriginQ / IBM 提交单元应在维护者确认 token、账号额度和后端

**Source code**

```{literalinclude} ../../../examples/3_best_practices/06_cloud_backend_template.py
:language: python
```

**Stdout**

```text
dummy dry-run success: True
details: Dry-run passed for dummy simulator: OriginIR is valid. Qubits=1, shots=100
originq API: submit_task(circuit, backend='originq', shots=1000, backend_name='PQPUMESH8')
ibm API: submit_task(circuit, backend='ibm', shots=1000, chip_id='ibm_fez')
```

