## 详细变更记录（自动整理）

这一节会在文档构建时根据当前仓库的 `git tag`、提交标题与变更文件路径整理生成。
这里主要提供可核对的版本变化记录；兼容性判断和升级建议以上面的说明为准。

### 版本总览

| 版本 | 日期 | 标题 |
| --- | --- | --- |
| `v0.0.12` | `2026-05-07` | v0.0.12 — uniqc-managed task ID indirection layer (uqt_*) + native batch + cloud error propagation |
| `v0.0.11.post1` | `2026-05-07` | v0.0.11.post1: chip-backed dummy relayout hotfix |
| `v0.0.11` | `2026-05-07` | Release 0.0.11 |
| `v0.0.10` | `2026-05-05` | Release v0.0.10 |
| `v0.0.9` | `2026-05-04` | v0.0.9: Calibration/QEM/XEB, calibrate CLI, dummy backend unification, 30+ bug fixes |
| `v0.0.8` | `2026-05-03` | v0.0.8 |
| `v0.0.7.post1` | `2026-05-02` | v0.0.7.post1: patch release — OriginQ simulator fix, dummy result persistence, IBM deps, chip-display, backend.md |
| `v0.0.7` | `2026-05-01` | v0.0.7: Circuit.get_matrix, chip-display CLI, AI-friendly help, chip characterisation data layer, enhanced transpiler, BackendOptions hierarchy, RegionSelector, dry-run validation, adapter result unification, Quafu expansion, ECR gate simulation fix |
| `v0.0.6` | `2026-04-29` | v0.0.6 — backend fidelity + IBM Target API |
| `v0.0.5` | `2026-04-21` | Merge pull request #17 from TMYTiMidlY/fix/cli-and-torchquantum-packaging |
| `v0.0.4.post1` | `2026-04-21` | Merge pull request #16 from TMYTiMidlY/fix/wheel-abi-mismatch |
| `v0.0.4` | `2026-04-19` | Merge pull request #6 from TMYTiMidlY/main |
| `v0.0.3` | `2026-04-18` | Merge pull request #1 from IAI-USTC-Quantum/fix/setuptools-scm-versioning |
| `v0.0.1` | `2026-04-18` | fix: correct false positive in QASM parser 'if' check |

## 开发中变更

- 说明：这一节展示自最新 tag 之后、当前 `HEAD` 上尚未形成新版本的变更。
- 对比区间：`v0.0.12..HEAD`
- 提交数：26
- 变更文件数：489

### 提交类型统计

| 类型 | 数量 |
| --- | ---: |
| `merge` | 7 |
| `docs` | 6 |
| `fix` | 5 |
| `feat` | 3 |
| `other` | 3 |
| `build` | 1 |
| `test` | 1 |

### 变更区域

- `docs`: 284 个文件
- `examples`: 71 个文件
- `example-exec-logs`: 50 个文件
- `uniqc/algorithms`: 22 个文件
- `uniqc/test`: 19 个文件
- `uniqc/backend_adapter`: 11 个文件
- `uniqc/calibration`: 5 个文件
- `uniqc/cli`: 4 个文件
- `scripts`: 3 个文件
- `.claude`: 2 个文件
- `uniqc/compile`: 2 个文件
- `.github`: 1 个文件
- `CHANGELOG.md`: 1 个文件
- `CONTRIBUTING.md`: 1 个文件
- `README.md`: 1 个文件
- `README_en.md`: 1 个文件
- `conftest.py`: 1 个文件
- `frontend`: 1 个文件
- `pyproject.toml`: 1 个文件
- `pytest.ini`: 1 个文件
- `uniqc/_error_hints.py`: 1 个文件
- `uniqc/config.py`: 1 个文件
- `uniqc/exceptions.py`: 1 个文件
- `uniqc/gateway`: 1 个文件
- `uniqc/qem`: 1 个文件
- `uniqc/utils`: 1 个文件
- `uniqc/visualization`: 1 个文件

### 提交列表

- `7a2a16d` fix(submit_task): enforce provider:chip-name format and fix auto-compile
- `2555f46` Merge remote-tracking branch 'origin/main' into feat/pre-submission-validation
- `ae88275` fix(adapters): enforce c[0]=LSB bitstring convention on Quafu and IBM/Qiskit
- `00adde1` test(doc-basic-usage): accept UnsupportedGateError when no chip cache
- `9301364` Merge pull request #83 from IAI-USTC-Quantum/feat/pre-submission-validation
- `f03d567` Merge main into fix/endian; resolve submit_task.md and skip originq dummy when uncached
- `c8d76d3` Merge pull request #84 from IAI-USTC-Quantum/fix/endian
- `2781a9b` feat: enrich all API error messages with doc links and troubleshooting hints
- `277dd82` Merge pull request #85 from IAI-USTC-Quantum/feat/error-hint
- `1d3b9c7` feat: promote qiskit to core dep, archive quafu extra
- `c51b4d1` fix: point error doc links to specific API pages instead of generic index
- `7f4dc9c` Merge pull request #86 from IAI-USTC-Quantum/feat/error-hint
- `15fa152` docs/frontend: surface Quark platform, hide Quafu from site
- `74dd05d` Merge pull request #87 from IAI-USTC-Quantum/feat/repair-dependencies
- `0548662` feat(calibration,backend): parallel-CZ XEB module + strict pre-flight policy
- `8398204` fix(test): gate dummy:originq endianness test on OriginQ credentials
- `c54019c` Merge pull request #88 from IAI-USTC-Quantum/feat/parallel-cz-xeb-and-preflight
- `16c7f9d` fix(cli,backend): JSON-serialize UnifiedResult; reject bare 'dummy'; flatten mps form
- `2b1c4e1` Merge pull request #89 from IAI-USTC-Quantum/fix/dummy-naming-and-cli-json
- `b72358a` build(docs): add two-step doc pipeline + switch theme to Furo
- `872399a` docs(examples): reorganize examples/ into chapter-numbered directories
- `b5a53d4` docs: replace 6-area structure with 8 chapter-numbered sections
- `53040fe` docs: commit example-exec-logs/ + _generated/ from initial pipeline run
- `68e9474` docs: update CONTRIBUTING / README / docstrings for new doc structure
- `089c634` docs(examples): pull aux dirs into chapter structure with directives
- `3678316` docs: restore deep prose + integrate aux examples + silence warning noise

## v0.0.12

- 发布日期：`2026-05-07`
- 发布标题：v0.0.12 — uniqc-managed task ID indirection layer (uqt_*) + native batch + cloud error propagation
- 补充说明：Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
- 对比区间：`v0.0.11.post1..v0.0.12`
- 提交数：3
- 变更文件数：12

### 提交类型统计

| 类型 | 数量 |
| --- | ---: |
| `chore` | 1 |
| `feat` | 1 |
| `other` | 1 |

### 变更区域

- `uniqc/backend_adapter`: 5 个文件
- `uniqc/gateway`: 2 个文件
- `uniqc/test`: 2 个文件
- `CHANGELOG.md`: 1 个文件
- `uniqc/__init__.py`: 1 个文件
- `uniqc/cli`: 1 个文件

### 提交列表

- `b9c3416` feat(batch): native batch submission for OriginQ + IBM (one task ID per batch)
- `a2fce31` Add uniqc-managed task ID indirection layer (uqt_*)
- `979dd9b` chore(release): v0.0.12

## v0.0.11.post1

- 发布日期：`2026-05-07`
- 发布标题：v0.0.11.post1: chip-backed dummy relayout hotfix
- 补充说明：Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
- 对比区间：`v0.0.11..v0.0.11.post1`
- 提交数：2
- 变更文件数：4

### 提交类型统计

| 类型 | 数量 |
| --- | ---: |
| `chore` | 1 |
| `fix` | 1 |

### 变更区域

- `CHANGELOG.md`: 1 个文件
- `uniqc/backend_adapter`: 1 个文件
- `uniqc/compile`: 1 个文件
- `uniqc/test`: 1 个文件

### 提交列表

- `487b2c9` fix(dummy): honour local_compile=0 and available_qubits in chip-backed dummy compile
- `7b31627` chore(release): v0.0.11.post1

## v0.0.11

- 发布日期：`2026-05-07`
- 发布标题：Release 0.0.11
- 补充说明：fix: surgical bug fixes from audit review
- 对比区间：`v0.0.10..v0.0.11`
- 提交数：30
- 变更文件数：141

### 提交类型统计

| 类型 | 数量 |
| --- | ---: |
| `fix` | 15 |
| `feat` | 5 |
| `docs` | 4 |
| `merge` | 3 |
| `other` | 2 |
| `release` | 1 |

### 变更区域

- `docs`: 33 个文件
- `uniqc/algorithms`: 20 个文件
- `uniqc/test`: 19 个文件
- `uniqc/backend_adapter`: 12 个文件
- `uniqc/compile`: 10 个文件
- `uniqc/circuit_builder`: 6 个文件
- `uniqc/cli`: 6 个文件
- `uniqc/simulator`: 5 个文件
- `examples`: 4 个文件
- `site`: 4 个文件
- `uniqc/calibration`: 4 个文件
- `uniqc/qem`: 4 个文件
- `uniqc/visualization`: 2 个文件
- `.claude`: 1 个文件
- `.github`: 1 个文件
- `.gitignore`: 1 个文件
- `CHANGELOG.md`: 1 个文件
- `README.md`: 1 个文件
- `README_en.md`: 1 个文件
- `pyproject.toml`: 1 个文件
- `uniqc/__init__.py`: 1 个文件
- `uniqc/config.py`: 1 个文件
- `uniqc/exceptions.py`: 1 个文件
- `uniqc/gateway`: 1 个文件
- `uniqc/torch_adapter`: 1 个文件

### 提交列表

- `4775a44` docs(skill): update uniqc-release to skip manual PyPI publish
- `96cd69f` docs(skill): add GitHub Release creation and branch cleanup to uniqc-release
- `fd14423` Merge pull request #70 from IAI-USTC-Quantum/codex/update-release-skill-pypi-auto
- `fc93df2` feat(site): add landing page, move docs to /docs/ subpath
- `831f768` feat(site): add AI Agent skills section for quantum-computing.skill
- `fa464ff` fix site script syntax
- `3743157` docs: update notebooks and backend descriptions
- `0a2dfbc` feat(compile): pre-submission validation + gate-depth API
- `19472dc` Merge pull request #71 from IAI-USTC-Quantum/feat/pre-submission-validation
- `9bfa93e` feat(simulator): add MPS simulator and dummy:mps:linear-N backend
- `d10ea89` fix: surgical bug fixes from audit review
- `9b0e895` fix: remove UNIQC_DUMMY env var — dummy mode by backend prefix only (D3)
- `ac129a2` fix: remove UNIQC_SKIP_VALIDATION env var — use skip_validation=True kwarg (D2)
- `69aa10f` fix: split validation into hard block (IR language) + soft skip_validation
- `bf06282` fix(api): resolve list_backends / get_backend naming inconsistencies (D8+B2)
- `61ced9a` fix(perf): add max_search_seconds timeout to find_best_1D_chain (D6)
- `e7aafba` docs: warn that deutsch_jozsa_circuit already includes MEASURE (C5)
- `ea4a758` fix(api): return ReadoutCalibrationResult dataclass from calibrate_1q/2q (E2)
- `d5bdf31` fix(backend): credential-aware platform fetch + fetch failure visibility (D11)
- `c6d7f47` fix(config): warn on unknown platform keys to catch typos (F9)
- `5ad16b0` fix(exceptions): consolidate exception system (issue #76)
- `0ebaf02` fix(test+docs): align with UnifiedResult contract and renamed exceptions
- `0bcf6ec` fix(audit-A): expose .get_matrix(), QASM def support, draw, doc fixes (A-U1..A-U7)
- `6b17150` fix(audit-B): simulator re-exports, factory order, density alias docs (B-U1..B-U7)
- `a8cea75` feat(audit-C-U1): refactor algorithms to circuit-fragment design
- `83bc1ad` fix(audit-batch1): no-decision cleanups across uniqc
- `cb44e7b` fix(audit-batch3): NEW-U1/U2/U4, C-U4/U6, D-U2/U3/U4/U6/U9/U10/U11/U13, E-U4/U5, F-U3
- `90af7a3` Round-4 audit fixes: A-U3, B-U5, B-U6, C-U2, C-U5, C-U9, E-U7, NEW-U2.b
- `367bf8a` release: 0.0.11 changelog + fix list_backends test for enriched chip-info entries
- `292ce9b` Merge pull request #80 from IAI-USTC-Quantum/fix/audit-review

## v0.0.10

- 发布日期：`2026-05-05`
- 发布标题：Release v0.0.10
- 补充说明：Release v0.0.10
- 对比区间：`v0.0.9..v0.0.10`
- 提交数：15
- 变更文件数：307

### 提交类型统计

| 类型 | 数量 |
| --- | ---: |
| `docs` | 5 |
| `merge` | 5 |
| `fix` | 2 |
| `feat` | 1 |
| `other` | 1 |
| `perf` | 1 |

### 变更区域

- `UniqcCpp`: 276 个文件
- `uniqc/test`: 6 个文件
- `docs`: 4 个文件
- `.github`: 3 个文件
- `uniqc/simulator`: 3 个文件
- `.claude`: 2 个文件
- `uniqc/algorithms`: 2 个文件
- `uniqc/backend_adapter`: 2 个文件
- `.gitmodules`: 1 个文件
- `CHANGELOG.md`: 1 个文件
- `CMakeLists.txt`: 1 个文件
- `CONTRIBUTING.md`: 1 个文件
- `README.md`: 1 个文件
- `README_en.md`: 1 个文件
- `pyproject.toml`: 1 个文件
- `scripts`: 1 个文件
- `setup.py`: 1 个文件

### 提交列表

- `0e4fd83` perf: cache classical shadow expectations
- `6449352` fix: run qem examples on noisy dummy backend
- `0496610` Merge pull request #65 from IAI-USTC-Quantum/codex/clear-open-issues
- `68cc897` Use PyPI pybind11 for C++ wheel builds
- `e0796bd` Merge pull request #66 from IAI-USTC-Quantum/codex/use-pypi-pybind11-cibw
- `8969ac4` fix: add ipython dependency to quark extras
- `18d693d` Merge pull request #67 from IAI-USTC-Quantum/fix/quark-ipython-dependency
- `d6fd062` feat(qiskit): detect and use system proxy when not explicitly configured
- `9ec9e33` docs(skill): add release skill and update test-before-release skill
- `324081b` Merge pull request #68 from IAI-USTC-Quantum/codex/qiskit-proxy-system-detection
- `611bca9` docs(release): prepare v0.0.10 release
- `ac53b29` docs(release): add v0.0.10 release notes to docs
- `7e3f39b` docs(skill): add docs release notes step to uniqc-release skill
- `2b9b22a` docs(skill): add docs release notes step to uniqc-release skill
- `b20a2d5` Merge pull request #69 from IAI-USTC-Quantum/release/v0.0.10

## v0.0.9

- 发布日期：`2026-05-04`
- 发布标题：v0.0.9: Calibration/QEM/XEB, calibrate CLI, dummy backend unification, 30+ bug fixes
- 补充说明：docs(release): prepare 0.0.9 release notes and changelog
- 对比区间：`v0.0.8..v0.0.9`
- 提交数：11
- 变更文件数：45

### 提交类型统计

| 类型 | 数量 |
| --- | ---: |
| `other` | 5 |
| `docs` | 2 |
| `merge` | 2 |
| `refactor` | 2 |

### 变更区域

- `uniqc/cli`: 11 个文件
- `docs`: 10 个文件
- `uniqc/backend_adapter`: 8 个文件
- `uniqc/test`: 6 个文件
- `.claude`: 3 个文件
- `CHANGELOG.md`: 1 个文件
- `README.md`: 1 个文件
- `frontend`: 1 个文件
- `uniqc/__init__.py`: 1 个文件
- `uniqc/compile`: 1 个文件
- `uniqc/config.py`: 1 个文件
- `uniqc/gateway`: 1 个文件

### 提交列表

- `a8eff8b` Add pre-release test skill
- `dd407ee` Address pre-release feedback and AI hints
- `f64dc1e` Promote config to top-level API
- `d90511f` Allow top-level config package boundary
- `4d209b0` Set gateway default port to 18765
- `ff8f0ed` docs(cli): add npx skills install guidance to help
- `c916de0` refactor: move task config loader to project top level
- `440b1fb` refactor: slim backend_adapter/config.py to compatibility shim
- `83dc2de` Merge pull request #60 from IAI-USTC-Quantum/codex/uniqc-test-before-release
- `c68271a` docs(release): prepare 0.0.9 release notes and changelog
- `f9ca191` Merge pull request #63 from IAI-USTC-Quantum/release/0.0.9

## v0.0.8

- 发布日期：`2026-05-03`
- 发布标题：v0.0.8
- 补充说明：[codex] add quark backend and cloud test gate
- 对比区间：`v0.0.7.post1..v0.0.8`
- 提交数：37
- 变更文件数：332

### 提交类型统计

| 类型 | 数量 |
| --- | ---: |
| `other` | 11 |
| `merge` | 10 |
| `docs` | 9 |
| `fix` | 4 |
| `ci` | 1 |
| `feat` | 1 |
| `test` | 1 |

### 变更区域

- `uniqc/test`: 71 个文件
- `docs`: 59 个文件
- `uniqc/algorithms`: 36 个文件
- `examples`: 29 个文件
- `uniqc/backend_adapter`: 28 个文件
- `frontend`: 18 个文件
- `uniqc/cli`: 15 个文件
- `uniqc/compile`: 14 个文件
- `uniqc/gateway`: 12 个文件
- `uniqc/calibration`: 9 个文件
- `uniqc/torch_adapter`: 5 个文件
- `uniqc/visualization`: 4 个文件
- `uniqc/qem`: 3 个文件
- `uniqc/utils`: 3 个文件
- `.github`: 2 个文件
- `scripts`: 2 个文件
- `uniqc/circuit_builder`: 2 个文件
- `uniqc/simulator`: 2 个文件
- `uniqc/task`: 2 个文件
- `uniqc/transpiler`: 2 个文件
- `.gitignore`: 1 个文件
- `CHANGELOG.md`: 1 个文件
- `CLAUDE.md`: 1 个文件
- `CONTRIBUTING.md`: 1 个文件
- `README.md`: 1 个文件
- `README_en.md`: 1 个文件
- `conftest.py`: 1 个文件
- `pyproject.toml`: 1 个文件
- `pytest.ini`: 1 个文件
- `stubgen.py`: 1 个文件
- `uniqc/__init__.py`: 1 个文件
- `uniqc/__main__.py`: 1 个文件
- `uniqc/analyzer`: 1 个文件
- `uniqc/version.py`: 1 个文件

### 提交列表

- `de5d87f` Merge pull request #50 from IAI-USTC-Quantum/fix/v0.0.7.post1
- `162e47f` docs: restore concept diagram and AI-native design positioning to README
- `07fb84d` docs: restore concept diagram and AI-native design positioning to README
- `136f46e` docs: add SkillHub badge to both READMEs
- `8ae6635` docs: update skill badge to link to GitHub repo
- `0f3346b` Merge pull request #51 from IAI-USTC-Quantum/docs/restore-readme-concept-diagram
- `2cd0953` docs: restore concept diagram, add English README, update Skill badge
- `1e0f523` Merge origin/main into docs/readme-final: resolve conflicts
- `3373992` Merge pull request #52 from IAI-USTC-Quantum/docs/readme-final
- `a48842c` docs: update release notes for v0.0.7 and v0.0.7.post1
- `6098094` Merge pull request #53 from IAI-USTC-Quantum/docs/release-notes-v0.0.7
- `e37aaf1` feat: add full calibration series — XEB, readout EM, M3, parallel patterns
- `c76dfb6` fix: XEB circuits, fitter, CLI, and DummyAdapter noisy simulation
- `e53e4f1` docs: update CHANGELOG, README, calibration guide, and CLI help text
- `c46a8a3` fix: real-hardware integration — OriginQ adapter defaults, polling, result parsing
- `a03fddb` fix: 2q XEB shape mismatch + backend availability validation
- `405d5a6` fix: noisy XEB pipeline — chip characterization, simulate_pmeasure, pairwise fitter
- `3c65ccd` docs: update CHANGELOG with Bug 17-20 fixes
- `96721a0` test: allow numpy_fallback_pairwise in fitter test method list
- `530b341` Refactor package architecture
- `184b8f0` Stop tracking uv lock and clean test artifacts
- `558902d` Merge pull request #54 from IAI-USTC-Quantum/feat/calibration-series
- `7032214` Polish docs and CLI guidance
- `3f643eb` Merge pull request #55 from IAI-USTC-Quantum/docs/polish-cli-readme-changelog
- `79c8646` align cloud config and test policy
- `b7ea01c` fix proxy precedence test on windows
- `a1518da` Merge pull request #56 from IAI-USTC-Quantum/codex/config-yaml-cloud-test-policy
- `64a5542` docs: add executable best practices notebooks
- `f55467b` ci: install pandoc for docs notebooks
- `9c66699` Merge pull request #57 from IAI-USTC-Quantum/codex/config-yaml-cloud-test-policy
- `11eda4c` add timeline scheduling and html rendering
- `289ed1c` Merge pull request #58 from IAI-USTC-Quantum/codex/timeline-scheduling-html
- `be9d6d1` add quark backend and cloud test gate
- `8c37c65` fix quafu ci skip and backend filters
- `81475f8` enrich quark backend metadata
- `1ef8bce` fix gateway spa direct routes
- `faf53e5` Merge pull request #59 from IAI-USTC-Quantum/codex/quark-backend-cloud-test-gate

## v0.0.7.post1

- 发布日期：`2026-05-02`
- 发布标题：v0.0.7.post1: patch release — OriginQ simulator fix, dummy result persistence, IBM deps, chip-display, backend.md
- 补充说明：1. require("pyqpanda3>=0.3.5", ...) -> require("pyqpanda3", ...) require() is __import__() underneath — version specifiers are not supported. Version lower bound is already in pyproject.toml.
- 对比区间：`v0.0.7..v0.0.7.post1`
- 提交数：6
- 变更文件数：19

### 提交类型统计

| 类型 | 数量 |
| --- | ---: |
| `fix` | 3 |
| `merge` | 2 |
| `other` | 1 |

### 变更区域

- `docs`: 8 个文件
- `uniqc/cli`: 3 个文件
- `uniqc/task`: 3 个文件
- `CHANGELOG.md`: 1 个文件
- `pyproject.toml`: 1 个文件
- `uniqc/config.py`: 1 个文件
- `uniqc/task_manager.py`: 1 个文件
- `uniqc/test`: 1 个文件

### 提交列表

- `ac206f8` Merge pull request #37 from Agony5757/fix/docs-pdf-build
- `7fc4e77` Merge pull request #38 from IAI-USTC-Quantum/fix/docs-pdf-build
- `58e852d` Merge upstream/main into fix/v0.0.7.post1
- `b9448e7` fix: address 5 blocking review comments from PR #49
- `b89f273` fix: remove QCloudSimulator — simulators use QCloudBackend.run() in pyqpanda3
- `b0ae001` fix: revert require() version specifier; fix submit_batch dummy routing

## v0.0.7

- 发布日期：`2026-05-01`
- 发布标题：v0.0.7: Circuit.get_matrix, chip-display CLI, AI-friendly help, chip characterisation data layer, enhanced transpiler, BackendOptions hierarchy, RegionSelector, dry-run validation, adapter result unification, Quafu expansion, ECR gate simulation fix
- 补充说明：- Collapse [Unreleased] into [0.0.7], merge all post-v0.0.6 commits: Circuit.get_matrix(), chip-display CLI, AI-friendly help, chip characterisation data layer, transpiler/BackendOptions/RegionSelector, dry-run validation, OriginQ adapter robustness, adapter result unification, Quafu expansion, ECR gate simulation fix - Update submit_task.md / testing.md: replace deprecated dummy=True with backend='dummy' - Add Circuit.get_matrix() section to circuit.md - Add Qiskit/matplotlib common-errors section to compiler_options_region.md
- 对比区间：`v0.0.6..v0.0.7`
- 提交数：30
- 变更文件数：88

### 提交类型统计

| 类型 | 数量 |
| --- | ---: |
| `docs` | 8 |
| `merge` | 8 |
| `feat` | 6 |
| `fix` | 3 |
| `refactor` | 3 |
| `other` | 1 |
| `style` | 1 |

### 变更区域

- `docs`: 29 个文件
- `uniqc/cli`: 13 个文件
- `uniqc/task`: 11 个文件
- `uniqc/test`: 9 个文件
- `UniqcCpp`: 3 个文件
- `examples`: 3 个文件
- `uniqc/algorithmics`: 3 个文件
- `uniqc/circuit_builder`: 2 个文件
- `uniqc/transpiler`: 2 个文件
- `CHANGELOG.md`: 1 个文件
- `CLAUDE.md`: 1 个文件
- `CMakeLists.txt`: 1 个文件
- `CONTRIBUTING.md`: 1 个文件
- `README.md`: 1 个文件
- `uniqc/__init__.py`: 1 个文件
- `uniqc/backend.py`: 1 个文件
- `uniqc/backend_info.py`: 1 个文件
- `uniqc/circuit_adapter.py`: 1 个文件
- `uniqc/originir`: 1 个文件
- `uniqc/region_selector.py`: 1 个文件
- `uniqc/simulator`: 1 个文件
- `uniqc/task_manager.py`: 1 个文件

### 提交列表

- `6767f34` feat(cli): AI-friendly help system with workflow hints and reference links
- `984edfd` feat(chip): unified chip characterization data layer with per-qubit fidelity and CLI
- `591870c` refactor: move chip-display into backend subcommand, remove separate chip CLI
- `ce60d81` fix: implement ECR gate simulation via native-gate decomposition
- `54f4f32` docs: add ECR gate to OriginIR and opcode reference
- `46189ff` Merge pull request #29 from Agony5757/feat/ai-friendly-cli-help
- `c93410d` refactor(cli): move chip modules into uniqc/cli/ and add --version flag
- `320ba76` Merge pull request #30 from IAI-USTC-Quantum/refactor/chip-cli-reorg
- `5b4cf9c` fix: compatibility adjustments for OriginQ adapter robustness
- `d5f2754` feat: Quafu gate expansion, IBMAdapter deprecation, and platform conventions docs
- `4c085ba` feat: migrate QiskitAdapter to qiskit-ibm-runtime API + Quafu adapter fixes
- `7e6d45e` docs: add CLI example with 4-qubit GHZ circuits and usage guide
- `ec0c22d` Merge pull request #31 from Agony5757/feature/originq-submit-chip-info
- `771998f` fix: unify adapter query() result to flat {bitstring: shots} dict
- `b85c1ef` feat: add offline dry-run validation to all cloud adapters
- `971fba1` Merge pull request #32 from Agony5757/fix/adapter-flat-result-format
- `bcedb77` Merge pull request #33 from Agony5757/feat/dry-run-validation
- `dedb78f` docs: add About Us section and Quantum|AI badge to README
- `c352645` Merge pull request #34 from Agony5757/docs/add-about-us-section
- `7d4625a` feat: add enhanced transpiler, typed BackendOptions, and RegionSelector
- `95035f1` refactor: add DummyBackend and chip-characterization noise simulation
- `f5ee30b` docs: update CONTRIBUTING.md and CLAUDE.md for uv dev environment
- `58496e8` style: ruff auto-fix unused imports and unsorted imports in dummy_adapter and task_manager
- `a1e1f3c` add compiler measurement probability checks
- `66c4e82` docs: update CHANGELOG for unreleased changes and fix section order
- `8c0aab8` Merge pull request #35 from Agony5757/feature/compiler-options-regionselector
- `3840590` docs: overhaul CLI docs — add backend command group, --dry-run, and platform conventions
- `cd955bb` Merge pull request #36 from Agony5757/main
- `0bc5c83` docs: fix PDF build and chapter structure
- `c650569` docs: finalize CHANGELOG for v0.0.7 and sync documentation

## v0.0.6

- 发布日期：`2026-04-29`
- 发布标题：v0.0.6 — backend fidelity + IBM Target API
- 补充说明：fix: IBM fidelity target API + docs/dev-setup updates
- 对比区间：`v0.0.5..v0.0.6`
- 提交数：23
- 变更文件数：35

### 提交类型统计

| 类型 | 数量 |
| --- | ---: |
| `merge` | 10 |
| `docs` | 6 |
| `fix` | 3 |
| `feat` | 2 |
| `ci` | 1 |
| `refactor` | 1 |

### 变更区域

- `uniqc/test`: 13 个文件
- `uniqc/task`: 5 个文件
- `docs`: 4 个文件
- `.github`: 2 个文件
- `uniqc/cli`: 2 个文件
- `CLAUDE.md`: 1 个文件
- `README.md`: 1 个文件
- `concept_unified_platforms.png`: 1 个文件
- `pyproject.toml`: 1 个文件
- `pytest.ini`: 1 个文件
- `uniqc/backend_cache.py`: 1 个文件
- `uniqc/backend_info.py`: 1 个文件
- `uniqc/backend_registry.py`: 1 个文件
- `uniqc/config.py`: 1 个文件

### 提交列表

- `6f37156` docs: polish release notes and fix tag docs deploy
- `340efe7` ci: allow docs deploys from release tags
- `bba1dc8` docs: add comprehensive OriginIR language specification
- `16f8367` Merge pull request #18 from Agony5757/docs/originir-spec
- `b3d3247` refactor: remove mock imports from tests, use real dependencies
- `04a0f54` fix(ci): remove bash-specific 2>/dev/null for Windows compatibility
- `1bee233` fix: add dill>=0.4.1 constraint to prevent qiskit compatibility issue
- `b7f5728` Merge pull request #21 from yowakkojay/fix/dill-version-constraint
- `d0a389e` Merge pull request #19 from Agony5757/refactor/remove-test-mocks
- `5e4ee2a` docs: enhance design philosophy section with AI-native positioning and concept diagram
- `d87395b` Merge pull request #22 from IAI-USTC-Quantum/docs/add-banner-to-readme
- `66ae427` docs: fix markdown table separator in design philosophy section
- `a520587` Merge pull request #23 from IAI-USTC-Quantum/docs/design-philosophy-table-fix
- `33cf085` docs: remove design philosophy table from README
- `57ca19e` Merge pull request #24 from IAI-USTC-Quantum/docs/remove-design-philosophy-table
- `65e3358` feat: install docs, OriginQ submit qubit count, backend registry and IBM adapter
- `37e52b5` Merge pull request #25 from Agony5757/feature/originq-submit-chip-info
- `0ebf1c0` docs: make uv primary install method, add Tsinghua mirror guidance
- `3235fad` Merge pull request #26 from Agony5757/docs/uv-install-recommended
- `0a66087` feat: enrich backend metadata with fidelity, coherence, and topology data
- `6cc81bd` Merge pull request #27 from Agony5757/feat/backend-fidelity-chip-info
- `7cec9a6` fix: IBM adapter uses correct Target API, update docs and dev setup
- `2615fb9` Merge pull request #28 from Agony5757/fix/backend-fidelity-ibm-target

## v0.0.5

- 发布日期：`2026-04-21`
- 发布标题：Merge pull request #17 from TMYTiMidlY/fix/cli-and-torchquantum-packaging
- 补充说明：fix: 修复 CLI 参数解析并移除 TorchQuantum 的 PyPI Git 依赖
- 对比区间：`v0.0.4.post1..v0.0.5`
- 提交数：11
- 变更文件数：37

### 提交类型统计

| 类型 | 数量 |
| --- | ---: |
| `other` | 5 |
| `fix` | 3 |
| `merge` | 2 |
| `docs` | 1 |

### 变更区域

- `uniqc/test`: 11 个文件
- `uniqc/cli`: 8 个文件
- `examples`: 5 个文件
- `uniqc/algorithmics`: 2 个文件
- `uniqc/simulator`: 2 个文件
- `uniqc/task`: 2 个文件
- `README.md`: 1 个文件
- `codecov.yml`: 1 个文件
- `pyproject.toml`: 1 个文件
- `uniqc/config.py`: 1 个文件
- `uniqc/originir`: 1 个文件
- `uniqc/pytorch`: 1 个文件
- `uniqc/qasm`: 1 个文件

### 提交列表

- `fc1466c` fix: scope simulation dependency checks by backend
- `054560a` docs: align simulation check docs and flags
- `d672e71` Merge pull request #15 from TMYTiMidlY/fix/simulation-check-scope
- `94dcf08` fix: unify CLI parsing and torchquantum packaging fallback
- `6980ba0` Fix eager imports for optional simulator deps
- `52b65af` Fix test mocks that poison uniqc_cpp imports
- `666cf82` Polish Copilot follow-up fixes
- `ff8dc2c` Preserve measurements when parsing OriginIR
- `b9f78b3` Relax Codecov patch threshold
- `b2fdbd0` fix(cli): resolve 4 CLI/parser bugs around QASM, results, and profiles
- `9a188b3` Merge pull request #17 from TMYTiMidlY/fix/cli-and-torchquantum-packaging

## v0.0.4.post1

- 发布日期：`2026-04-21`
- 发布标题：Merge pull request #16 from TMYTiMidlY/fix/wheel-abi-mismatch
- 补充说明：修复 wheel 构建绑定错误 Python 解释器导致的 ABI 不匹配
- 对比区间：`v0.0.4..v0.0.4.post1`
- 提交数：18
- 变更文件数：50

### 提交类型统计

| 类型 | 数量 |
| --- | ---: |
| `merge` | 6 |
| `fix` | 5 |
| `docs` | 2 |
| `test` | 2 |
| `chore` | 1 |
| `feat` | 1 |
| `refactor` | 1 |

### 变更区域

- `uniqc/test`: 10 个文件
- `docs`: 8 个文件
- `examples`: 7 个文件
- `uniqc/algorithmics`: 6 个文件
- `.github`: 5 个文件
- `scripts`: 2 个文件
- `uniqc/pytorch`: 2 个文件
- `uniqc/simulator`: 2 个文件
- `.gitignore`: 1 个文件
- `CLAUDE.md`: 1 个文件
- `CONTRIBUTING.md`: 1 个文件
- `README.md`: 1 个文件
- `pyproject.toml`: 1 个文件
- `setup.py`: 1 个文件
- `uniqc/cli`: 1 个文件
- `uniqc/transpiler`: 1 个文件

### 提交列表

- `edb676d` fix: remove duplicate release trigger from pypi-publish workflow
- `92d0113` Merge pull request #7 from Agony5757/fix/pypi-publish-duplicate-trigger
- `7d81b06` refactor: remove --no-cpp option and require C++ build
- `ebd7356` Merge pull request #8 from Agony5757/refactor/remove-no-cpp
- `b5becb6` fix: resolve issue #9 - documentation and code consistency fixes
- `ed88afb` test: add tests for CLI, transpiler, simulator, and test runner
- `65157dd` Merge pull request #10 from Agony5757/fix/issue-9-doc-code-consistency
- `28d6e08` feat: add TorchQuantum backend and variational quantum algorithms
- `523177f` fix: resolve CI build failures
- `f8168ea` fix: exclude qiskit transpiler tests from CI (dill serialization conflict)
- `9af1aa8` Merge pull request #11 from Agony5757/feature/torchquantum-backend
- `71c3d29` docs: add release notes page
- `98bbab2` docs: document release notes maintenance
- `68ec0dc` Merge pull request #12 from TMYTiMidlY/docs/release-notes-page
- `214192f` fix: bind wheel builds to the active Python interpreter
- `8278631` test: validate wheel ABI tags in CI
- `54d7065` chore: clarify wheel ABI validation errors
- `60a838e` Merge pull request #16 from TMYTiMidlY/fix/wheel-abi-mismatch

## v0.0.4

- 发布日期：`2026-04-19`
- 发布标题：Merge pull request #6 from TMYTiMidlY/main
- 补充说明：refactor!: 任务缓存统一迁至 SQLite + 重命名 uniq → uniqc + 文档整顿
- 对比区间：`v0.0.3..v0.0.4`
- 提交数：11
- 变更文件数：792

### 提交类型统计

| 类型 | 数量 |
| --- | ---: |
| `docs` | 5 |
| `refactor` | 3 |
| `merge` | 2 |
| `chore` | 1 |

### 变更区域

- `UniqcCpp`: 508 个文件
- `docs`: 71 个文件
- `uniqc/test`: 66 个文件
- `examples`: 27 个文件
- `uniqc/algorithmics`: 26 个文件
- `uniqc/task`: 13 个文件
- `uniqc/circuit_builder`: 11 个文件
- `uniqc/cli`: 10 个文件
- `uniqc/simulator`: 9 个文件
- `uniqc/transpiler`: 6 个文件
- `UniqCpp`: 5 个文件
- `uniqc/analyzer`: 4 个文件
- `uniqc/pytorch`: 4 个文件
- `uniqc/qasm`: 4 个文件
- `.github`: 3 个文件
- `uniq`: 3 个文件
- `uniqc/originir`: 3 个文件
- `.gitignore`: 1 个文件
- `.gitmodules`: 1 个文件
- `CLAUDE.md`: 1 个文件
- `CMakeLists.txt`: 1 个文件
- `README.md`: 1 个文件
- `banner_uniqc.png`: 1 个文件
- `pyproject.toml`: 1 个文件
- `pytest.ini`: 1 个文件
- `setup.py`: 1 个文件
- `stubgen.py`: 1 个文件
- `uniqc/__init__.py`: 1 个文件
- `uniqc/__main__.py`: 1 个文件
- `uniqc/backend.py`: 1 个文件
- `uniqc/circuit_adapter.py`: 1 个文件
- `uniqc/config.py`: 1 个文件
- `uniqc/exceptions.py`: 1 个文件
- `uniqc/network_utils.py`: 1 个文件
- `uniqc/task_manager.py`: 1 个文件
- `uniqc/version.py`: 1 个文件

### 提交列表

- `68e6ac6` docs: add banner to README.md
- `aa48271` Merge pull request #2 from IAI-USTC-Quantum/docs/add-banner-to-readme
- `d56689a` refactor: unify task cache on SQLite; polish README and CLI
- `cb26368` refactor: rename CLI binary from `uniq` to `uniqc`
- `ae0e226` refactor!: rename package uniq -> uniqc; purge qpanda-lite residue
- `7856839` docs: clean up rename residues and tighten sphinx config
- `e2ff258` docs: reconcile design docs with current implementation
- `566f27d` docs: fix rendering bugs in index and docstrings
- `be0d3f2` docs: regenerate API reference via sphinx-apidoc, stop tracking generated rst
- `6b1f908` chore: clean up dead version macro, BOM, and misleading README comment
- `999ab59` Merge pull request #6 from TMYTiMidlY/main

## v0.0.3

- 发布日期：`2026-04-18`
- 发布标题：Merge pull request #1 from IAI-USTC-Quantum/fix/setuptools-scm-versioning
- 补充说明：fix: correct setuptools_scm version detection in CI workflows
- 对比区间：`v0.0.1..v0.0.3`
- 提交数：2
- 变更文件数：4

### 提交类型统计

| 类型 | 数量 |
| --- | ---: |
| `fix` | 1 |
| `merge` | 1 |

### 变更区域

- `.github`: 2 个文件
- `.gitignore`: 1 个文件
- `uniq`: 1 个文件

### 提交列表

- `9059921` fix: correct setuptools_scm version detection in CI workflows
- `d977728` Merge pull request #1 from IAI-USTC-Quantum/fix/setuptools-scm-versioning

## v0.0.1

- 发布日期：`2026-04-18`
- 发布标题：fix: correct false positive in QASM parser 'if' check
- 补充说明：The parser used substring match ('if' in qasm) which triggered on "Unified" in "UnifiedQuantum" within auto-generated comments. Changed comment to use "uniq" and added TODO for proper regex-based check.
- 对比区间：`repo start -> v0.0.1`
- 提交数：6
- 变更文件数：805

### 提交类型统计

| 类型 | 数量 |
| --- | ---: |
| `fix` | 5 |
| `other` | 1 |

### 变更区域

- `UniqCpp`: 510 个文件
- `uniq`: 165 个文件
- `docs`: 78 个文件
- `examples`: 33 个文件
- `.github`: 5 个文件
- `.gitattributes`: 1 个文件
- `.gitignore`: 1 个文件
- `.gitmodules`: 1 个文件
- `.pre-commit-config.yaml`: 1 个文件
- `CLAUDE.md`: 1 个文件
- `CMakeLists.txt`: 1 个文件
- `CODE_OF_CONDUCT.md`: 1 个文件
- `CONTRIBUTING.md`: 1 个文件
- `LICENSE`: 1 个文件
- `README.md`: 1 个文件
- `pyproject.toml`: 1 个文件
- `pytest.ini`: 1 个文件
- `setup.py`: 1 个文件
- `stubgen.py`: 1 个文件

### 提交列表

- `a9761ed` Initial commit: UnifiedQuantum migrated from QPanda-lite
- `ce17725` fix: use explicit dependencies in 'all' extra
- `ad11537` fix: mark QASM tests as xfail due to unsupported if statements
- `856f589` fix: disable setuptools_scm local scheme to avoid invalid wheel filename
- `9c0106b` fix: use API token for PyPI publishing to support first release
- `5215648` fix: correct false positive in QASM parser 'if' check
