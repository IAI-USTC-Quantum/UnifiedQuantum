"""Centralized reference URLs and AI workflow hints for the CLI."""

from __future__ import annotations

# ----------------------------------------------------------------------
# Base URLs
# ----------------------------------------------------------------------
GITHUB_URL = "https://github.com/IAI-USTC-Quantum/UnifiedQuantum"
DOCS_URL = "https://iai-ustc-quantum.github.io/UnifiedQuantum/"

# ----------------------------------------------------------------------
# Reference links shown in --help under each command
# Structure: {command_name: [(label, url), ...]}
# ----------------------------------------------------------------------
CMD_REFS: dict[str, list[tuple[str, str]]] = {
    "circuit": [
        ("CLI Docs", f"{DOCS_URL}cli.html#uniqc-circuit"),
        ("GitHub", GITHUB_URL),
    ],
    "simulate": [
        ("CLI Docs", f"{DOCS_URL}cli.html#uniqc-simulate"),
        ("GitHub", GITHUB_URL),
    ],
    "submit": [
        ("CLI Docs", f"{DOCS_URL}cli.html#uniqc-submit"),
        ("GitHub", GITHUB_URL),
    ],
    "result": [
        ("CLI Docs", f"{DOCS_URL}cli.html#uniqc-result"),
        ("GitHub", GITHUB_URL),
    ],
    "task-list": [
        ("CLI Docs", f"{DOCS_URL}cli.html#uniqc-task-list"),
        ("GitHub", GITHUB_URL),
    ],
    "task-show": [
        ("CLI Docs", f"{DOCS_URL}cli.html#uniqc-task-show"),
        ("GitHub", GITHUB_URL),
    ],
    "backend-list": [
        ("CLI Docs", f"{DOCS_URL}cli.html#uniqc-backend"),
        ("GitHub", GITHUB_URL),
    ],
    "backend-show": [
        ("CLI Docs", f"{DOCS_URL}cli.html#uniqc-backend"),
        ("GitHub", GITHUB_URL),
    ],
    "config": [
        ("CLI Docs", f"{DOCS_URL}cli.html#uniqc-config"),
        ("GitHub", GITHUB_URL),
    ],
}

# ----------------------------------------------------------------------
# AI workflow hints — "next steps" and "what to do if X" guidance.
# Each entry is a list of (label, text) tuples.
# Shown via --ai-hints flag or UNIQC_AI_HINTS=1 env var.
# ----------------------------------------------------------------------
AI_HINTS: dict[str, list[tuple[str, str]]] = {
    "circuit": [
        (
            "Format auto-detection",
            "uniqc circuit circuit.qasm auto-detects OriginIR vs QASM from file content. "
            "Use --format originir or --format qasm to force a specific output format.",
        ),
        (
            "Getting started with circuit building",
            "Use the Python API: from uniqc.circuit_builder import Circuit. "
            "See the docs for a full circuit builder guide.",
        ),
        (
            "Show circuit statistics",
            "Pass --info to see gate count, circuit depth, and qubit count without converting.",
        ),
    ],
    "simulate": [
        (
            "Statevector vs density matrix",
            "--backend statevector (default) gives exact probabilities and is fast. "
            "--backend density models noise and is useful for NISQ device simulation.",
        ),
        (
            "Choosing shot count",
            "Default 1024 shots is good for quick results. "
            "Use 10000+ for better statistics on high-noise hardware backends.",
        ),
        (
            "Saving results",
            "Pass --output results.json --format json to write machine-readable output to a file.",
        ),
        (
            "Next: submit to a real backend",
            "After finding a good circuit locally, use uniqc backend list to pick a backend, "
            "then uniqc submit circuit.qasm --platform originq --backend <NAME>.",
        ),
    ],
    "submit": [
        (
            "After submitting — get your result",
            "Run uniqc result <TASK_ID> to retrieve results. "
            "Or use uniqc task list to see all tasks and their statuses.",
        ),
        (
            "Wait for result without polling",
            "Pass --wait (or -w) to block until the task completes, up to --timeout seconds.",
        ),
        (
            "Authentication error?",
            "Run uniqc config validate to check your token, or "
            "uniqc config set originq.token <YOUR_TOKEN> to set it.",
        ),
        (
            "Wrong platform?",
            "Re-run with --platform originq|quafu|ibm. "
            "Use uniqc backend list --platform <PLATFORM> to see available backends first.",
        ),
        (
            "Picking the right backend",
            "Run uniqc backend list to see backends, then pass the full name with --backend. "
            "Example: --backend 'originq:origin:wuyuan:d5'",
        ),
    ],
    "result": [
        (
            "No result yet?",
            "If the task is still pending/running, pass --wait (or -w) to poll until it completes. "
            "Default timeout is 300 seconds; use --timeout 600 to extend.",
        ),
        (
            "Task not found?",
            "Run uniqc task list to see all submitted tasks across all platforms. "
            "Check if the task_id is correct — IDs are case-sensitive.",
        ),
        (
            "See all tasks",
            "uniqc task list shows every submitted task with its status (pending/running/success/failed). "
            "Use --platform originq to filter by platform.",
        ),
        (
            "Result is empty?",
            "The backend may not have returned counts yet. "
            "Try --wait again, or check uniqc task show <TASK_ID> for detailed task status.",
        ),
    ],
    "task-list": [
        (
            "No tasks shown?",
            "1. Configure your platform token: uniqc config set originq.token <TOKEN>\n"
            "   (Token URLs: OriginQ: q.本源量子.com | Quafu: quafu.baike.scut.cn | IBM: quantum.ibm.com)\n"
            "2. Validate: uniqc config validate\n"
            "3. Retry: uniqc task list",
        ),
        (
            "Wrong platform?",
            "Filter by platform: uniqc task list --platform originq. "
            "Supported platforms: originq, quafu, ibm.",
        ),
        (
            "Filter by status",
            "Use --status pending|running|success|failed to narrow the list. "
            "Completed tasks can be cleared with uniqc task clear.",
        ),
        (
            "Get a task's result",
            "Run uniqc result <TASK_ID> to fetch the result for any task shown here.",
        ),
    ],
    "task-show": [
        (
            "Get the measurement result",
            "Run uniqc result <TASK_ID> to fetch the measurement counts and probabilities.",
        ),
        (
            "Task still running?",
            "Use uniqc result <TASK_ID> --wait to poll until it completes.",
        ),
        (
            "See all tasks",
            "Run uniqc task list to see all submitted tasks, not just one.",
        ),
    ],
    "backend-list": [
        (
            "No backends listed?",
            "Run uniqc backend update to fetch the latest backend list from all configured platforms. "
            "Backend data is cached for 24 hours; --all shows even unavailable backends.",
        ),
        (
            "Select a backend for submission",
            "Copy the Name column value (e.g., originq:origin:wuyuan:d5) and pass it to "
            "uniqc submit circuit.qasm --platform originq --backend 'originq:origin:wuyuan:d5'",
        ),
        (
            "Hardware vs simulator",
            "Backends marked 'hw' are real quantum hardware; 'sim' are simulators. "
            "Hardware backends have noise but test real device behavior. "
            "Use --status hardware or --status simulator to filter.",
        ),
        (
            "Filter by platform",
            "Run uniqc backend list --platform originq to see only one platform's backends.",
        ),
        (
            "Stale cache?",
            "Run uniqc backend update to force-refresh. Use --clear to wipe the cache first.",
        ),
    ],
    "backend-show": [
        (
            "Use this backend for submission",
            "Pass the full identifier to --backend: "
            "uniqc submit circuit.qasm --platform originq --backend 'originq:origin:wuyuan:d5'",
        ),
        (
            "Compare backends",
            "Run uniqc backend list --info to see fidelity and coherence data for all backends at once.",
        ),
        (
            "Hardware backends have noise",
            "Real hardware backends (hw) show avg_1q_fidelity and avg_2q_fidelity. "
            "Lower fidelity means higher error rates on real devices.",
        ),
    ],
    "config": [
        (
            "First-time setup (step by step)",
            "1. uniqc config init — create ~/.uniqc/uniqc.yml with default settings\n"
            "2. uniqc config set originq.token <YOUR_TOKEN> — set your API token\n"
            "   (Token URLs: OriginQ: q.本源量子.com | Quafu: quafu.baike.scut.cn | IBM: quantum.ibm.com)\n"
            "3. uniqc config validate — verify the configuration is valid\n"
            "4. uniqc backend update — fetch available backends",
        ),
        (
            "Get your API token",
            "OriginQ: https://q.本源量子.com\n"
            "Quafu: https://quafu.baike.scut.cn/\n"
            "IBM: https://quantum.ibm.com/",
        ),
        (
            "After configuring",
            "Run uniqc backend update to fetch available backends, "
            "then uniqc backend list to pick one for submission.",
        ),
        (
            "Multiple profiles",
            "Use --profile my-profile to work with a named profile. "
            "Create one with: uniqc config profile create my-profile\n"
            "Switch profiles with: uniqc config profile use my-profile",
        ),
    ],
    "backend-chip-display": [
        (
            "What is chip characterization data?",
            "Per-qubit T1/T2, gate fidelities, readout errors, and connectivity — "
            "used to pick the best qubits for your experiment or to model noise.",
        ),
        (
            "Syntax reminder",
            "Use platform/chip_name format: uniqc backend chip-display originq/wuyuan:d5",
        ),
        (
            "Refresh stale data",
            "If chip calibration was updated on the cloud, pass --update (or -u) to re-fetch: "
            "uniqc backend chip-display originq/wuyuan:d5 --update",
        ),
        (
            "Next: use for qubit selection",
            "Chip characterization data can be used programmatically to select optimal qubit "
            "subgraphs for your circuit — see the analyzer module for qubit-picking utilities.",
        ),
    ],
}
