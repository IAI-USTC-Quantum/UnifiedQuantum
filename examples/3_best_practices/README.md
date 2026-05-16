# Best Practices Examples

11 release-time path-check scripts. Each example carries a docstring directive
header (`[doc-require: ...]`, `[doc-warning-ignore: ...]`, ...) consumed by
`scripts/build_docs.py` so the docs build can decide whether to (re-)run it.

| File | Coverage |
|------|----------|
| `00_config_and_backend_cache.py` | config save/load/validate, backend cache write/read/audit |
| `01_bare_circuit_simulation.py` | Bell state, OriginIR/QASM export, local simulator + plot |
| `02_named_circuit_and_reuse.py` | `@circuit_def`, named registers, composition |
| `03_compile_region_dummy_backend.py` | `compile(...)` to a virtual-line-3 backend |
| `04_api_submit_dummy_result.py` | `submit_task` → `wait_for_result` on `dummy:local:simulator` |
| `05_cli_workflow_dummy.py` | `uniqc submit --backend dummy:local:simulator` end-to-end via subprocess |
| `06_cloud_backend_template.py` | safe template: `dry_run_task` then real-cloud snippets |
| `07_variational_circuit.py` | parameter-shift loop minimizing `<Z>` |
| `08_torch_quantum_training.py` | torch optimizer + parameter-shift gradient |
| `09_calibration_qem_dummy.py` | readout calibration + `ReadoutEM` mitigation |
| `10_xeb_workflow_dummy.py` | end-to-end 1q XEB workflow with noise model |

Run a single example directly:

```bash
uv run python examples/3_best_practices/01_bare_circuit_simulation.py
```

Run the whole batch through the doc pipeline (writes `example-exec-logs/` and
`docs/source/_generated/examples/`):

```bash
uv run python scripts/build_docs.py --only 3_best_practices
```
