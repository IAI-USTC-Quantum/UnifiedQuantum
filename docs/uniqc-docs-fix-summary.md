# UnifiedQuantum docs fix summary (uniqc 0.0.11.dev10)

> Note: written here instead of `/tmp/uniqc-docs-fix-summary.md` because the
> runtime forbids writing to `/tmp`.

- [FIXED docs/source/guide/circuit.md:58] A1 — removed `xy` from 双量子比特门 list (verified `Circuit().xy` does not exist).
- [FIXED docs/source/guide/circuit.md:139-154] A2 — replaced 提取酉矩阵 section: dropped non-existent `Circuit.get_matrix()` / `NotMatrixableError`; replaced with note recommending `OriginIR_Simulator(backend_type='statevector').simulate_statevector(circuit.originir)`.
- [FIXED docs/source/guide/circuit.md:217-226] A3 — `Parameter.evaluate(values=...)` example now shows that bound value wins; demonstrates calling `unbind()` first to make the dict take effect.
- [FIXED docs/source/guide/compiler_options_region.md:81-95] A4 — rewrote 1.5 `TranspilerConfig` section: real `compile()` signature does not accept `config=`; show spreading TranspilerConfig fields into kwargs with `find_backend('originq:WK_C180')`; clarified `compile()` returns `Circuit | str`, and `CompilationResult` is internal to `compile_full()` (not exported).
- [FIXED docs/source/guide/compiler_options_region.md:505-512] A5 — added qiskit-extra callout to the `plot_time_line()` / `schedule_circuit` matplotlib note explaining `compile()` dependency on `unified-quantum[qiskit]`.
- [FIXED docs/source/guide/simulation.md:118-126] B1 — noisy quickstart now constructs `OriginIR_NoisySimulator(backend_type='density_matrix', ...)` with explanatory note about `ValueError` on `statevector`.
- [FIXED docs/source/advanced/mps_simulator.md:53] B5 — `chi_max` default corrected from 256 to 64; added note about memory ∝ N·χ²·d².
- [FIXED docs/source/guide/simulation.md:43-50, 150-157] B6 — added `MPSSimulator` and `TorchQuantumSimulator` rows to the entry-overview table and to the API list, plus mention of `create_simulator(backend=...)` factory and `unified-quantum[pytorch]` extra + torchquantum git note.
- [FIXED docs/source/advanced/noise_simulation.md:15-38, 58-65] B7 — quickstart now imports `ErrorLoader_GenericError`; usage example now imports `TwoQubitDepolarizing`. Both snippets are self-contained.
- [FIXED docs/source/cli/installation.md:5-13] F6 — added callout that `python -m uniqc` is no longer supported; use `uniqc` or `python -m uniqc.cli`.
- [FIXED docs/source/guide/pytorch.md:37-66, 104-121, 127-145, 172-200] F7 — replaced `circuit_template=...` / `param_names=[...]` calls with the actual `QuantumLayer(circuit, expectation_fn, n_outputs=1, init_params=None, shift=π/2)` signature; removed manual `theta.bind`/`theta.evaluate()` template builders in favour of passing pre-built `Circuit` whose `_parameters` are auto-introspected; updated VQE example to use `vqe_layer.parameters()` for the optimizer (since the layer now owns its own `nn.Parameter`); added explanatory line about auto-extracted param names.
- [FIXED docs/source/cli/task.md:51] F8 — replaced `--status completed` with `--status success` and added note that valid values are `pending / running / success / failed`.

No fixes were skipped.
