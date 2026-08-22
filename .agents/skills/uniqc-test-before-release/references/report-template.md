# Pre-Release Test Report Template

Use this exact top-level structure. Keep evidence concrete: command, commit, artifact path, task ID, or URL.

## Verdict

Recommendation: `RELEASE` / `RELEASE WITH KNOWN GAPS` / `DO NOT RELEASE`

One-paragraph rationale.

## Release Candidate

- Repository:
- Branch:
- Commit:
- Tag/version candidate:
- Test start/end time:
- Tester/agent:
- Machine/OS/Python/Node:

## Executive Summary

| Area | Status | Evidence | Notes |
|---|---|---|---|
| Python tests |  |  |  |
| Best practices |  |  |  |
| CLI |  |  |  |
| AI hints |  |  |  |
| Docs alignment |  |  |  |
| Gateway frontend |  |  |  |
| Gateway API |  |  |  |
| Cloud discovery |  |  |  |
| Real-device execution |  |  |  |
| Calibration/QEM/XEB |  |  |  |

## Blocking Issues

List release blockers first. For each item include:

- Severity:
- Affected area:
- Evidence:
- Reproduction:
- Expected:
- Actual:
- Suggested owner/fix:

## Non-Blocking Gaps

List accepted gaps. Include who accepted the risk and why it does not block release.

## Environment and Setup

Include dependency commands, package versions, `uv run uniqc --version` if available, `uv run uniqc --help` availability, and frontend dependency state.

## Best-Practices Validation

For each best-practices notebook:

- File:
- Execution status:
- Key output checked:
- Doc/software mismatch found:

End with a statement on whether the best-practices chapter is aligned with software behavior.

## CLI Validation

Include captured help commands and behavioral CLI workflows. Explicitly state whether the docs match the help output.

Also include whether `--ai-hints` / `--ai-hint`, `UNIQC_AI_HINTS=1`, and `uniqc config always-ai-hint on` were checked.

## Gateway Frontend/API Validation

Include build result, server command, API endpoints checked, frontend rendering method, and any visual testing gaps.

## Cloud and Real-Device Validation

Separate discovery, dry-run, and real execution. For real tasks include backend, shots, task ID, submission time, result retrieval time, and result summary.

## Programmatic Documentation Alignment

Describe every scripted or manual comparison:

- Comparison:
- Source files:
- Command/script:
- Result:
- Mismatches:

## Final Recommendation

Repeat the verdict and list the exact conditions that must change before release if the answer is not `RELEASE`.
