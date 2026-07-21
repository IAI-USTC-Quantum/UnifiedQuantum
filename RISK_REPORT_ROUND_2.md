# UnifiedQuantum (`uniqc`) Risk Report — Round 2

本报告保留首轮风险报告的全部标题与发现，并在每个原始条目后追加当前维护者处置结论。状态基于
`77538e6`、`906699c`、`a403b47`、`540ebf2`、`440162c`、`a9b2336`、`8d7ef6d` 及当前 `main`。

## 1. Release & Supply Chain (highest blast radius)

### HIGH — PyPI publishing gated only by tag push, using a long-lived token
- `.github/workflows/pypi-publish.yml:51-53` passes `password: ${{ secrets.PYPI_API_TOKEN }}` to `gh-action-pypi-publish`.
- `id-token: write` at line 43 shows trusted publishing (OIDC) was intended but never completed — the permission is unused while `password` is set.
- No `environment:` gate, no manual approval, no `workflow_dispatch` fallback (lines 3-6, 38-43): anyone who can push a `v*` tag publishes to PyPI immediately. A leaked token is valid until manually revoked.

**维护者回应 — 状态：接受风险/无需修改。** 本项目明确决定继续使用现有 PyPI API token，不引入
GitHub Environment approval gate，也不增加人工批准或 `workflow_dispatch`。Environment gate 的作用是把
部署 job 绑定到受保护环境，并可配置审批人、等待时间和环境级 secret；它适合需要独立发布审批的团队，
但不是本项目当前流程要求。`id-token: write` 仍为发布 action/未来 Trusted Publishing 迁移保留；当前实际认证
仍由 token 完成。为避免“任意 `v*` tag 即发布”的主要误触风险，`77538e6` 已增加阻塞式
`validate_release`：tag 必须位于 `main` 历史中、tag/version/`CHANGELOG.md` 必须一致，且每个 wheel 的版本必须
匹配 tag；构建和发布 job 均依赖这些检查通过。

### MEDIUM — Mutable personal-fork dependency executed in CI, unpinned
- `pytest_coverage.yml:110-111` and `build_and_test.yml:137-138` run:
  `uv pip install "torchquantum @ git+https://github.com/Agony5757/torchquantum.git@fix/optional-qiskit-deps"` — a branch ref, not a commit SHA, on a personal fork. A force-push to that branch executes arbitrary code in CI.
- Note: every GitHub Action in all 5 workflows **is** full-SHA pinned (verified by grep); this fork is the one gap.

**维护者回应 — 状态：已修复。** `77538e6` 将可变 Git branch 安装替换为已发布的
`torchquantum-ng` 包；它保留 `torchquantum` import 名称，同时移除旧版强制 dill/TensorFlow 依赖。首轮所说
“Actions full-SHA pinned”是指 `uses: owner/action@...` 使用不可变提交 SHA，而不是可移动的 `v4` 等标签，可降低
上游 tag 被重指向后的供应链风险。`8d7ef6d` 同步修正 runtime error hints 与 advanced examples，不再向用户推荐
旧 Git branch。当前工作流 action 继续全部 SHA 固定，并已补充 workflow 级最小权限。

### MEDIUM — Release publishes no sdist and no macOS wheels
- `pypi-publish.yml:15` builds wheels only on `ubuntu-latest`/`windows-latest` via cibuildwheel; no sdist step anywhere; publish job (lines 46-53) uploads only `wheelhouse/*.whl`.
- `pyproject.toml:94` also skips musllinux → macOS/aarch64/musl users have no installable artifact.

**维护者回应 — 状态：接受风险/无需修改。** 项目有意不发布 sdist。正式保证并发布预编译 wheel 的平台为
Windows/Linux；macOS、musllinux、aarch64 等其他平台仅按 best effort 支持源码编译，不承诺兼容性。
`README.md` 与 `README_en.md` 的 Supported Platforms 已在 `a9b2336` 明确记录该边界。

### HIGH — Unpinned runtime deps enforced by test, with known upstream breakage
- `pyproject.toml:34-48` (numpy, scipy, sympy, fastapi, qiskit, qiskit-aer, qiskit-ibm-runtime…) carries zero constraints.
- `uniqc/test/test_dependency_policy.py:42-51` actively **fails** if anyone adds any version operator — even an upper bound.
- Risk is not hypothetical: CI comments document a qiskit/dill pickle breakage (`pytest_coverage.yml:74-81`).

**维护者回应 — 状态：接受风险/无需修改。** 不固定运行时依赖及其测试约束是明确的项目策略，用于尽早暴露
上游兼容性变化。qiskit/dill 问题指旧 TorchQuantum 依赖 dill，而 dill 会改变/扩展序列化路径，曾与 qiskit
transpiler 对象的 pickle 行为冲突；这不是要求固定 qiskit 的结论。`77538e6` 通过改用
`torchquantum-ng` 并从 `[all]` 删除 dill 消除了该已知组合，而非改变无版本约束策略。

### MEDIUM — CI "dill-free environment" contradicts installed extras
- `pyproject.toml:81` lists `dill` in `[all]` (added in `530b341`); both workflows install `.[all]` (`pytest_coverage.yml:69`, `build_and_test.yml:104`) then claim the main suite runs in a "dill-free environment" (`pytest_coverage.yml:83`, `build_and_test.yml:116`). Either the documented qiskit-transpiler breakage is live in the main suite, or the two-phase workaround is stale cargo.

**维护者回应 — 状态：已修复。** dill 原先是旧 TorchQuantum 路径的传递/辅助依赖，并非 uniqc 核心功能所需。
`77538e6` 已从 `[all]` 删除 dill，CI 使用 `torchquantum-ng`，并把核心功能测试与 TorchQuantum 定向测试清晰
分开；“dill-free”描述与实际安装环境现已统一。

### MEDIUM — "Release gate" is an AI-skill note; release reports leave dangling references
- Commit `c09d2ab` implements the gate as 2 lines in `.claude/skills/uniqc-test-before-release/SKILL.md` — procedural, assistant-enforced, not CI.
- HEAD commit `5555b2c` deleted `RELEASE_REPORT_0.0.16.md` the same day v0.0.16 shipped, yet `CHANGELOG.md:14-15` and `docs/source/7_releases/index.md:85` still point readers to it (same stale pattern for 0.0.15 at `CHANGELOG.md:48`).

**维护者回应 — 状态：已修复。** AI skill 仍是有意保留的人工流程辅助，但不再承担唯一发布门禁。
`77538e6` 增加了真实 CI 阻塞验证。`a9b2336` 将发布报告的规范位置统一为
`docs/source/7_releases/reports/`，恢复 `docs/source/7_releases/reports/0.0.16.md`，并修复
`CHANGELOG.md` 与发布索引引用；后续 release report 不再放仓库根目录。

### LOW — Coverage upload & permissions
- Codecov step (`pytest_coverage.yml:140-143`) uses long-lived `CODECOV_TOKEN`, no `if: always()`, no `fail_ci_if_error` — fork PRs silently skip uploads.
- No `permissions:` block in `build_and_test.yml`, `pytest_coverage.yml`, `python_build_wheel.yml`.
- `docs.yml:32-35` grants `pages: write` + `id-token: write` at workflow level (only the deploy job is gated, line 99).
- `build_and_test.yml:174-180` uploads `.coverage`, but its pytest run (line 121) never passes `--cov` — the step silently uploads nothing.
- Any `v*` tag publishes; no check the tag is on `main` or matches `CHANGELOG.md`.

**维护者回应 — 状态：部分已修复，部分接受风险/无需修改。** `77538e6` 为
`build_and_test.yml`、`pytest_coverage.yml`、`python_build_wheel.yml` 增加 `permissions: contents: read`；
permissions block 用于把默认 `GITHUB_TOKEN` 权限收敛到 job 实际需要的最小集合。Coverage/Codecov 继续是信息性：
上传步骤使用 `if: always()`，并显式 `fail_ci_if_error: false`，fork 无 secret 时不阻塞。
`build_and_test.yml` 中未实际生成 `.coverage` 的旧 artifact 上传按维护者决定保持不变；`docs.yml` 的 Pages/OIDC
权限布局同样本轮不变并接受风险。发布侧已通过 `scripts/check_release.py` 阻塞检查
tag 位于 `main`、版本与 `CHANGELOG.md` 一致、wheel 版本一致；无需 Environment gate。

**Verified clean:** no `pull_request_target`, no PR-title/branch interpolation in `run:` blocks, all actions SHA-pinned, version 0.0.16 consistent (tag `v0.0.16`, `CHANGELOG.md:10`, dynamic setuptools_scm).

**维护者回应 — 状态：接受风险/无需修改。** 这些正向结论继续成立。Action SHA pin 是对 GitHub Action
执行代码的不可变引用控制；它与 Python 包是否固定版本是两类独立策略。

---

## 2. Test & Build Health

### CRITICAL — Coverage runs never fail CI
- `pytest_coverage.yml:97` and `:131` append `|| true` to both coverage pytest runs.
- `pytest.ini` has no `--cov-fail-under`; `codecov.yml:1-6` sets only a *patch* status (`target: auto, threshold: 5%`) with no project gate. The coverage number is purely informational; a coverage collapse merges green.

**维护者回应 — 状态：接受风险/无需修改。** Coverage 明确保持信息性，不设置覆盖率阈值或合并门禁。
`77538e6` 删除含糊的 `|| true`，改为语义明确的 `continue-on-error: true`；同时先运行不带 coverage 的阻塞式
功能测试，再运行信息性 coverage pass。这样测试失败仍会阻塞，而 coverage 插桩/上传失败不会阻塞。

### HIGH — Zero C++ unit tests; "test" binary is a demo
- `UniqcCpp/test/main.cpp:22-31` is a scratch `main()` printing a bit-transform example, not a test.
- No gtest/ctest exists; the `UnifiedQuantumTest` executable is built but never invoked — no `ctest`/`UnifiedQuantumTest` reference in any workflow. The C++ simulator core (`simulator.cpp`, `density_operator_simulator.cpp`, …) is only exercised via Python bindings.

**维护者回应 — 状态：已修复（按既定范围）。** `a403b47` 将 demo 改为不引入 gtest 的手工 C++ smoke
可执行程序，并在 CMake 中注册，覆盖代表性基础调用和结果断言。维护策略仍是：不建设“覆盖所有 C++ 函数”的独立
C++ 单元测试体系，不增加框架复杂度；核心行为继续主要由 Python binding 测试覆盖，C++ smoke 仅作为开发者手工
运行的快速检查，不加入 CI 强制门禁。

### MEDIUM — Thin test clusters
- Test functions per dir vs source modules: `compile` 9 funcs/1 file vs 18 src modules; `visualization` 5/1 vs 4; `integration` 5/1; `benchmark` 2/2; `torch_adapter` 33/1 vs 6; `algorithms` 25 direct vs 46 src modules (partly offset by `algorithmics`' 181).
- Heavy clusters: `circuit_builder` 655, `cloud` 251.

**维护者回应 — 状态：delayed（下一轮继续跟踪）。** 本轮不扩展薄弱测试簇；后续按真实缺陷和变更风险定向补测，
不以目录函数数量均衡本身作为重构目标。

### MEDIUM — Unseeded RNG + global seed mutation
- `uniqc/test/calibration/test_xeb_fitter.py:74` uses `np.random.normal` unseeded and asserts `approx(abs=0.02)` (`:77`); `:94` calls global `np.random.seed(42)` mid-session, making outcomes order-dependent.
- Elsewhere hygiene is good: 73 seeded vs 8 unseeded uses, zero `time.sleep`, zero xfail.

**维护者回应 — 状态：delayed（下一轮继续跟踪）。** 本轮不修改 RNG 测试；下一轮优先改为局部
`numpy.random.Generator`，避免全局 seed 污染，同时保留现有正向测试卫生。

### MEDIUM — Stub drift detected manually; stale legacy stub shipped
- `uniqc/simulator/uniq_cpp.pyi` is a pre-rename stub for the defunct module `uniq_cpp` (last touched by rename commit `ae0e226`).
- `uniqc_cpp.pyi` went stale twice and was hand-regenerated (`4f32a14`, `68de154`); no workflow regenerates or diffs stubs (`python_build_wheel.yml:21` only path-triggers on `scripts/stubgen.py`).

**维护者回应 — 状态：delayed（下一轮继续跟踪）。** 本轮不处理 legacy stub 或自动漂移门禁；下一轮评估删除
`uniq_cpp.pyi` 并在 wheel/build 流程中加入可重复的 stub 生成与 diff 检查。

### MEDIUM — Deprecation "gate" always passes
- `build_and_test.yml:152-172`, named "fail on error", ends with `|| echo "::warning::…"` — exit code always 0.

**维护者回应 — 状态：delayed（下一轮继续跟踪）。** 本轮保持警告式 deprecation 检查；在 0.1.0 移除窗口前
再将其升级为阻塞门禁，避免当前 0.0.x 开发被既有弃用调用无差别阻塞。

### LOW — Misc
- Dead marker `requires_provider_chip_cache` declared (`pytest.ini:18`) but never used or handled in `conftest.py:56-134`.
- `docs/requirements.txt` fully unpinned and diverges from the `pyproject.toml:123-136` docs group; `docs.yml:63` uses requirements.txt, so the dependency-group is dead config.
- `.gitmodules` tracks fmt `branch = master` (checkout pinned at `3081c64` mitigates).
- `setup.py:38` `int(os.environ["DEBUG"])` crashes on non-numeric values.
- Positive: `build/` is gitignored; gateway tests are hermetic via tmp_path SQLite (`uniqc/test/gateway/conftest.py:15-37`); marker/credential gating is comprehensive.

**维护者回应 — 状态：部分已修复，部分 delayed。** `a403b47` 已删除重复的
`docs/requirements.txt` 依赖清单并让 docs CI 统一安装 `pyproject.toml` 的 docs dependency group；同时移除
`setup.py` 对非必要 `DEBUG` 环境变量的整数强制解析。dead marker 与 `.gitmodules` branch 声明
**delayed（下一轮继续跟踪）**。已确认的 gitignore、gateway 测试隔离和 credential marker 优点继续保留。

---

## 3. Security & Secrets

### MEDIUM — Gateway: wildcard CORS + unauthenticated mutating API
- `uniqc/gateway/server.py:46-52`: `allow_origins=["*"]`, `allow_credentials=True`, `allow_methods=["*"]` — `allow_credentials=True` with `*` is also a CORS spec violation.
- State-changing routes with no auth dependency: `uniqc/gateway/api/tasks.py:127` (DELETE task), `:137` (bulk-delete), `:151` (bulk-archive), `:177` (archive-expired), `api/archive.py:96` (DELETE), `api/backends.py:370` (POST refresh).
- Any website open in the user's browser can issue cross-origin state-changing requests to the local gateway. Risk grows with `uniqc gateway start --host 0.0.0.0` — accepted and persisted with no warning (`uniqc/gateway/cli.py:103-113`). Default host is safely `127.0.0.1` (`gateway/config.py:11`).

**维护者回应 — 状态：已修复（本地网关威胁模型）。** CORS 决定浏览器页面是否可以从不同 origin 调用网关；
通配 origin 配合凭据会扩大本地跨站请求面。`540ebf2` 将允许源限制为 localhost/127.0.0.1/IPv6 loopback 的
Vite 开发 origin，并对非 loopback bind 做拒绝/警告与配置约束。Gateway 的产品定位仍是 local-only，
因此本轮不增加登录、session 或 API token 鉴权；不得把它作为公网管理服务部署。

### LOW — CLI prints token prefixes
- `uniqc/cli/config_cmd.py:116-117` prints first 8 chars of a configured token; `uniqc/cli/doctor.py:45-48` prints first 6 chars. Partial disclosure into terminal scrollback/recordings/pasted doctor output.

**维护者回应 — 状态：已修复。** `540ebf2` 将配置与 doctor 输出改为完整 redaction，不再显示任何 token 前缀，
并新增 CLI 回归测试。

### LOW — Quafu token re-persisted by third-party SDK outside uniqc's 0600-protected config
- `uniqc/backend_adapter/task/adapters/quafu_adapter.py:393-394` (also 576-577, 621-622, 660-661, 781-782) calls `user.save_apitoken()`; the pyquafu SDK writes the token to disk a second time with location/permissions uniqc does not control.

**维护者回应 — 状态：接受风险/无需修改。** Quafu 已全局 deprecated，并在 `440162c` 从 `import uniqc`
关键路径移除为显式兼容性 lazy load；为避免在临近删除时扩大改动，本轮不重写第三方 token 持久化行为。
兼容路径保留到 0.1.0，届时删除。

### LOW — `exec()` on file contents in docs build
- `docs/conf.py:102` — `exec(_version_file.read_text())`. Build-time only, repo-controlled file; unnecessary code-exec primitive.

**维护者回应 — 状态：已修复。** `a403b47` 删除 docs 对生成 `_version.py` 的 `exec()`，改用
`setuptools_scm`、git tag 和已安装 package metadata 的受控版本解析。可选替代方案包括
`importlib.metadata.version()`、直接调用 `setuptools_scm.get_version()`，或只解析静态常量；当前实现按
release/dev 场景组合这些安全来源并提供 fallback。

### LOW — `pickle.load` in benchmark test
- `uniqc/test/benchmark/test_QASMBench.py:20` unpickles `QASMBench.pkl` — test-only, but classic RCE vector if the dataset source is untrusted.

**维护者回应 — 状态：已修复（保留 pickle）。** `906699c` 在反序列化前读取原始 bytes 并校验固定
SHA-256，摘要不匹配则拒绝且绝不调用 `pickle.loads`。pickle 仍因现有 fixture 的便利和性能保留，并明确只接受
仓库内可信、不可变数据。更彻底的替代方案是 JSON/msgpack/NPZ/Arrow 等非任意代码对象格式，但会要求迁移 fixture
schema；本轮无需迁移。

### Verified clean
- **No hardcoded credentials** anywhere (source, docs, examples, exec logs); only placeholders like `originq-token-redacted`. `.gitignore` covers `.env`, `*.log`, cloud config JSONs.
- **Config storage well-hardened:** `uniqc/config.py:118` uses `yaml.safe_load`; writes via `os.open(..., 0o600)` with temp-file + atomic `os.replace` (`config.py:147-174`); config dir created `0o700` (`config.py:140`); covered by `uniqc/test/test_config_file_perms.py`.
- **No dangerous calls in first-party code:** no `shell=True`, `os.system`, `verify=False`, untrusted archive extraction. QASM parameter evaluation uses an AST allow-list evaluator (`uniqc/compile/qasm/_safe_eval.py:10-16`) with RCE-rejection tests.
- **Network endpoints all TLS;** IBM token goes only into an `Authorization: Bearer` header (`network_utils.py:234`), not logs.

**维护者回应 — 状态：接受风险/无需修改。** 这些安全基线继续保留；本轮完整 token redaction 与 gateway
local-only 加固进一步减少了意外泄露和浏览器跨站调用面。

---

## 4. Code Architecture & Quality

### HIGH — God module: `task_manager.py` (2,269 lines / 87 KB, largest file)
- `uniqc/backend_adapter/task_manager.py` carries submission (`submit_task`:922, `submit_batch`:1280), dummy-backend paths (`_submit_dummy`:1168, `_submit_batch_dummy`:1528), querying (`query_task`:1765, `wait_for_result`:1987), shard aggregation, persistence, error mapping — *plus* a `TaskManager` class (2174-2269) that is a pure pass-through duplicating the module-level API: two parallel public APIs for the same logic in one file.

**维护者回应 — 状态：delayed（下一轮继续跟踪）。** 建议按稳定 façade + 内部服务拆分：保留现有
module-level API 兼容层；将输入准备/策略解析、单任务与 batch submission、dummy execution、poll/query/wait、
shard aggregation、persistence 分别迁入小模块；`TaskManager` 要么成为持有 store/backend registry 的真实实例服务，
要么在弃用周期后移除纯 pass-through 重复 API。重构必须先建立 golden behavior/公共导入兼容测试，分阶段迁移，
本轮不做大范围结构修改。

### HIGH — God class: `Circuit` (~1,930 lines, 125 methods)
- `uniqc/circuit_builder/qcircuit.py:125-2057` (file: 2,057 lines / 82 KB). The core domain object also does format conversion, decomposition, and parsing via deferred imports of `compile` (qcircuit.py:524,557), mixing layers into one class.

**维护者回应 — 状态：delayed（下一轮继续跟踪）。** 建议让 `Circuit` 聚焦 opcode/domain state 与编辑操作；
把 OriginIR/QASM reader/writer 移到 codec 层，把 decomposition/transformation 移到 compile pass，把展示/导出便捷方法
保留为薄 façade 委托。先引入无行为变化的内部 service，再逐步迁移方法，保持 `Circuit.from_*`/`to_*` 公共 API，
避免一次性拆类破坏用户代码。本轮仅记录方向，不实施重构。

### HIGH — Inverted/tangled subpackage layering
- `backend_adapter` → `cli` at 13 sites, top-level at `region_selector.py:39`, `quafu_adapter.py:51`, `quark_adapter.py:33` — the data layer depends on CLI modules (`chip_info`/`chip_cache` are data-model/persistence libraries misplaced under `cli/`).
- `gateway` → `cli` (`gateway/api/backends.py:21-22`); `calibration` → `cli` (`xeb/topology.py:31`).
- `compile` ↔ `visualization`: `compile/draw.py:3`, `compile/timeline.py:3` vs `visualization/circuit.py:11`, `timeline.py:447,550` — mutual, mitigated by function-local imports.
- `circuit_builder` ↔ `compile`: cycle worked around via 6 deferred function-local imports (qcircuit.py:524,557; classical_program.py:582,698; normalize.py:51,59).

**维护者回应 — 状态：delayed（下一轮继续跟踪）。** 问题不是功能立即错误，而是低层库反向依赖 CLI/UI，
以及包间双向引用导致 import cycle、局部延迟导入和测试隔离困难。建议目标方向为：
`domain/circuit_builder` → 独立 codec/IR contracts → `compile` → backend services；CLI、gateway、visualization、
calibration 只作为上层消费者。具体应把 `chip_info`/`chip_cache` 下沉到 backend/core service，把 drawing/timeline 的
共享数据模型放到中立模块，compile 产出数据而 visualization 渲染；Circuit 不直接依赖 compile 实现。先通过
dependency tests/导入图锁定方向，再小步迁移。本轮不做架构重排。

### MEDIUM — Deprecated Quafu path still eagerly wired
- `quafu_adapter.py:25` warns at import ("removed in 0.1.0"), yet is imported eagerly by `adapters/__init__.py:43` → `backend.py:52` → `uniqc/__init__.py:57`, so the deprecated module sits on the `import uniqc` critical path; workflows still reference it (`readout_em_workflow.py:30`, `xeb_workflow.py:37`).

**维护者回应 — 状态：已修复。** `440162c` 已取消 Quafu eager wire：普通 `import uniqc` 不再导入
Quafu adapter 或触发弃用警告；仅当用户显式选择 Quafu/导入兼容符号时 lazy load 并提示弃用。工作流引用也改为
按需加载。Quafu 兼容能力明确保留到 0.1.0，届时删除，不在本轮进一步重构。

### MEDIUM — Broad exception swallowing hides failures
- 133 `except Exception` in non-test code (35 files); 21 immediately `pass`.
- Worst: `ibm_adapter.py` (17 total; silent `pass`/`return None` at 35,46,66,91,104,131,145,162,222-238 — calibration parse failures silently yield `None`/`[]` data, i.e. potentially wrong results invisibly).
- `normalize.py:96-125` swallows real parser errors before a last-ditch re-parse; `task_manager.py:674-681` returns `None` on any resolution error. One bare `except:` (`store.py:270`, migration, comment-justified).

**维护者回应 — 状态：部分已修复；剩余 delayed（下一轮继续跟踪）。** `440162c` 仅对高风险、可精确定义
语义的路径做 targeted exception 修复：IBM calibration 解析区分缺字段/类型错误并保留可诊断上下文；
`normalize.py` 不再吞掉真实 parser 错误；`task_manager.py` 的 resolution fallback 仅捕获预期异常；相关回归测试位于
`uniqc/test/test_exception_paths.py`。没有机械替换全部 broad catch，因为边界层的兼容探测、可选依赖和迁移恢复
有时确实需要宽捕获。其余 broad catches 将逐项审计，明确“可恢复/需记录/必须抛出”契约后处理。

### LOW — Duplication hotspots
- `_avg` duplicated verbatim incl. docstring in 4 adapters (`ibm_adapter.py:23`, `originq_adapter.py:30`, `quafu_adapter.py:88`, `quark_adapter.py:100`); adapter pairs share 11-12 identically-named defs (originq 950 / quafu 938 / dummy 799 lines).

**维护者回应 — 状态：delayed（下一轮继续跟踪）。** 待 adapter 边界与 Quafu 0.1.0 删除完成后再抽取共享统计/
解析 helper，避免现在为即将删除的兼容路径建立新的公共抽象。

### LOW — Dead/stub code
- `qem/zne.py:1-20` is an unimplemented placeholder (`raise NotImplementedError`).
- `backend_adapter/database_migration.py` is docs-as-code, unreferenced by any module, duplicating `MIGRATIONS` in `store.py` — drift risk.
- TODO density is low: 5 markers total.

**维护者回应 — 状态：delayed（下一轮继续跟踪）。** ZNE placeholder 与 migration 文档重复本轮不动；下一轮决定
ZNE 是实现、标记 experimental 还是移除，并将 migration 文档改为从唯一数据源生成或删除。低 TODO 密度是正向信号。

---

## 5. Docs, Examples & Project-State Drift

### HIGH — `uniqc gateway` invocation documented wrong (missing `start`)
- Docs/examples say `uniqc gateway --host 127.0.0.1 --port 8000`, but `gateway` is a Typer group with `no_args_is_help=True` and no callback (`uniqc/gateway/cli.py:20-22`); the real command is `uniqc gateway start …` (`cli.py:101-102`).
- Wrong in `docs/source/5_webui/index.md:10`, `examples/5_webui/01_gateway_demo.py:11,43`, and propagated into committed artifacts `docs/source/_generated/examples/5_webui/01_gateway_demo.md:11,34` and `example-exec-logs/5_webui/01_gateway_demo/run.json:10`. (`docs/source/4_cli/gateway.md:19` is correct.)

**维护者回应 — 状态：已修复。** `a9b2336` 已统一为 `uniqc gateway start ...`，并刷新生成文档和执行日志，
避免源示例与 committed artifacts 再次漂移。

### HIGH — README links to non-existent `examples/algorithms/`
- `README.md:283-284` and `README_en.md:265-266` link `examples/algorithms/grover.md` and `qpe.md`; real files are at `examples/2_advanced/algorithms/grover.md` / `qpe.md`.

**维护者回应 — 状态：已修复。** `a9b2336` 修正中英文 README 链接到实际路径。

### MEDIUM — Referenced `RELEASE_REPORT_0.0.16.md` missing
- `CHANGELOG.md:15` and `docs/source/7_releases/index.md:85` point to a file absent from disk and git (see §1).

**维护者回应 — 状态：已修复。** 发布报告规范目录确定为
`docs/source/7_releases/reports/`；`a9b2336` 恢复 `0.0.16.md` 并修复所有引用。根目录不再作为 release report
的长期位置。

### MEDIUM — Committed exec logs/generated docs leak developer absolute paths
- `example-exec-logs/3_best_practices/05_cli_workflow_dummy/run.json:10` and `docs/source/_generated/examples/3_best_practices/05_cli_workflow_dummy.md` embed `/home/agony/projects/UnifiedQuantum/docs/../.venv/bin/python3`. Tokens are properly redacted; only `127.0.0.1` hosts appear.

**维护者回应 — 状态：已修复。** `a9b2336` 刷新并规范化生成产物，移除开发者绝对路径；token redaction 和
loopback host 约束继续保留。

### MEDIUM — README omits v0.0.16's headline feature and 4 CLI commands
- `README.md:79` / `README_en.md:79` omit `dummy:virtual:<name>`, the flagship v0.0.16 feature (`CHANGELOG.md:11-15`; implemented in `uniqc/backend_adapter/dummy_backend.py:164,188,264`).
- CLI Quick Reference never mentions registered `doctor`, `task`, `circuit`, `gateway` commands (`uniqc/cli/main.py:68-77`). All README-documented commands were verified to exist with matching flags.

**维护者回应 — 状态：已修复。** `a9b2336` 在中英文 README 增加 `dummy:virtual:<name>`、虚拟 backend
说明以及 `doctor`、`task`、`circuit`、`gateway` CLI 入口。

### LOW — Quafu messaging self-contradictory
- `README.md:17,104,231` advertise Quafu aggregation while `README.md:203` declares Quafu archived; `docs/index.md` already drops Quafu. Examples still template quafu backends (`examples/3_best_practices/06_cloud_backend_template.py:27,29`).

**维护者回应 — 状态：已修复。** `a9b2336` 统一 README、docs、examples 的平台叙述，Quafu 不再作为当前推荐
聚合平台展示；`440162c` 保留显式 lazy compatibility 到 0.1.0。

### LOW — Generated artifacts and binaries committed (by design, with side effects)
- 66 files under `docs/source/_generated/`, 155 autodoc stubs in `docs/source/6_api/`, all of `example-exec-logs/` — deliberate pipeline (`scripts/build_docs.py`, CI gate `scripts/check_doc_logs.py`), but it amplifies doc errors and leaks dev paths.
- Root tracks `banner_uniqc.png` (1.1 MB) and `concept_unified_platforms.png` (4.0 MB); README loads the banner from a raw.githubusercontent URL pinned to stale tag `v0.0.5` (`README.md:2`).
- `uniqc/_version.py` is tracked despite its own header "don't track in version control" and a matching gitignore rule.
- `frontend/` (React/Vite SPA for the gateway, 18 source files, last commit `15fa152`) and `site/` (4-file landing page deployed by `docs.yml:83-85`) are maintained, not abandoned.

**维护者回应 — 状态：已修复/接受风险。** 生成 docs、autodoc stubs 与 `example-exec-logs/` 是有意维护并提交的
输出，用于 review 与 CI 漂移检测；不删除，代价是必须在源修复后同步刷新。`a9b2336` 已完成本轮刷新和路径清理。
README banner 改为仓库内相对路径，避免固定旧 tag；`concept_unified_platforms.png` 同样作为维护中的品牌/说明资产
保留。`uniqc/_version.py` 是 setuptools_scm 构建生成物；复核当前基线确认它本就不在 git index 中，并继续由
`.gitignore` 管理，不应跟踪。`a403b47` 同步调整 package-structure 测试以允许 build/editable install 临时生成该文件。
`frontend/` 是本地 gateway UI 源码，`site/` 是 landing page 源码，两者都是有意维护输出，不是待清理的构建垃圾，
无需“修复”或删除。

---

## Strengths worth keeping

- Credential/config hygiene: no hardcoded secrets, 0600/0700 atomic config writes, `yaml.safe_load`, redacted example logs.
- CI trigger hygiene: all actions SHA-pinned, no `pull_request_target`, no script injection via PR metadata.
- Test hermeticity: comprehensive marker/credential gating, tmp_path SQLite for gateway tests, no `time.sleep`, no xfail clusters.
- Docs pipeline is deliberate and CI-gated (generated artifacts refreshed by commits) — it just amplifies whatever errors enter it.
- Version references mutually consistent (0.0.16 across tag, CHANGELOG, setuptools_scm).

**维护者回应 — 状态：接受风险/无需修改。** 上述优势全部保留。本轮进一步增加 release CI 验证、workflow
最小权限、依赖清理、gateway local-only/CORS 加固、完整 token redaction、可信 pickle 摘要校验、docs 安全版本解析，
并明确 generated docs/logs、frontend/site 和品牌图片均为有意维护的仓库输出。
