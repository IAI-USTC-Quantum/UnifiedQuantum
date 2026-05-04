# Coverage Matrix

Use this checklist when generating the detailed execution plan and final report.

| Area | Minimum checks | Release blocker examples |
|---|---|---|
| Install | `uv sync --all-extras --group dev --group docs --upgrade`; package import; CLI entry present | maintained extra cannot resolve; `uniqc` command missing |
| Python API | `Circuit`, top-level imports, compile/transpile, simulator, task manager | recommended import path broken; compile produces invalid circuit |
| Dummy backends | `dummy`, `dummy:virtual-line-N`, `dummy:virtual-grid-RxC`, `dummy:<platform>:<backend>` | chip-backed dummy listed as enumerable backend; topology constraints ignored |
| CLI | root help, subcommand help, simulate, submit, result, config, task, backend, calibrate, workflow, gateway | docs command missing from help; `python -m uniqc.cli` broken |
| Best practices | regenerate notebooks; inspect all `docs/source/best_practices/*.ipynb`; build docs | notebook execution failure; stale outputs; docs contradict behavior |
| Docs alignment | CLI help vs docs; pyproject scripts vs docs; deprecated imports scan | docs recommend removed command/API; config path mismatch |
| Gateway backend | `uniqc gateway start/status`; `/api/health`; `/api/version`; `/api/backends`; `/api/tasks` | server cannot start; API schema incompatible with frontend |
| Gateway frontend | `npm ci`; `npm run build`; loaded built app; backend/task pages | TypeScript build failure; blank frontend; backend cards wrong |
| Cloud discovery | OriginQ/IBM/Quark token/status/list/cache update where configured | configured platform cannot list backends without external cause |
| Real execution | authorized small-shot real task; task ID; result retrieval; cache record | submitted task cannot be queried; result normalizer broken |
| Calibration/QEM/XEB | readout/XEB dummy path; calibration cache; QEM TTL behavior | calibration file unusable; QEM silently uses stale data |
| Persistence | task cache, backend cache, archive store, config profiles | cache corruption, wrong profile, task lost after restart |

Coverage labels:

- `PASS`: executed and matched expected behavior.
- `FAIL`: executed and failed.
- `BLOCKED`: external missing credential, quota, network, or SDK; include exact blocker.
- `NOT RUN`: not attempted; include why and who accepted the risk.
