# Best Practices Examples

12 release-time path-check scripts. Each example carries a docstring directive
header (`[doc-require: ...]`, `[doc-warning-ignore: ...]`, ...) consumed by
[`scripts/build_docs.py`](../../scripts/build_docs.py) so the docs build can decide whether to (re-)run it.

| File | Coverage |
|------|----------|
| `00_config_and_backend_cache.py` | config save/load/validate, backend cache write/read/audit |
| `01_bare_circuit_simulation.py` | Bell state, [OriginIR](https://iai-ustc-quantum.github.io/UnifiedQuantum/docs/source/1_basic_usage/originir.html)/[QASM](https://iai-ustc-quantum.github.io/UnifiedQuantum/docs/source/1_basic_usage/qasm.html) export, [local simulator](https://iai-ustc-quantum.github.io/UnifiedQuantum/docs/source/1_basic_usage/simulation.html) + plot |
| `02_named_circuit_and_reuse.py` | `@circuit_def`, named registers, composition |
| `03_compile_region_dummy_backend.py` | `compile(...)` to a virtual-line-3 backend |
| `04_api_submit_dummy_result.py` | [`submit_task`](https://iai-ustc-quantum.github.io/UnifiedQuantum/docs/source/1_basic_usage/submit_task.html) → [`wait_for_result`](https://iai-ustc-quantum.github.io/UnifiedQuantum/docs/source/1_basic_usage/task_manager.html) on `dummy:local:simulator` |
| `05_cli_workflow_dummy.py` | `uniqc submit --backend dummy:local:simulator` end-to-end via subprocess |
| `06_cloud_backend_template.py` | safe template: `dry_run_task` then real-cloud snippets |
| `07_variational_circuit.py` | parameter-shift loop minimizing `<Z>` |
| `08_torch_quantum_training.py` | torch optimizer + parameter-shift gradient |
| `09_calibration_qem_dummy.py` | [readout calibration](https://iai-ustc-quantum.github.io/UnifiedQuantum/docs/source/4_cli/calibrate.html) + [`ReadoutEM`](https://iai-ustc-quantum.github.io/UnifiedQuantum/docs/source/6_api/index.html) mitigation |
| `10_xeb_workflow_dummy.py` | end-to-end 1q [XEB](https://iai-ustc-quantum.github.io/UnifiedQuantum/docs/source/2_advanced/calibration.html) workflow with noise model |
| `11_native_torch_training.py` | native `expectation()` with `has_param` / `param_dict` / tensor |

Run a single example directly:

```bash
uv run python examples/3_best_practices/01_bare_circuit_simulation.py
```

Run the whole batch through the doc pipeline (writes `example-exec-logs/` and
`docs/source/_generated/examples/`):

```bash
uv run python scripts/build_docs.py --only 3_best_practices
```
