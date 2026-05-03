"""Quantum computing task management module.

This package provides a unified interface for submitting and querying
quantum computing tasks across multiple backend platforms:

- ``originq`` — Origin Quantum Cloud (本源量子云) via pyqpanda3.
- ``quafu`` — BAQIS ScQ quantum cloud platform (Quafu).
- ``ibm`` — IBM Quantum via Qiskit Runtime.
- ``dummy`` — Local C++ simulator (no network, no credentials needed).

Public API (from ``uniqc.backend_adapter.task_manager``):

- ``submit_task`` — Submit a single circuit for execution.
- ``submit_batch`` — Submit multiple circuits as a batch.
- ``dry_run_task`` — Validate a circuit offline without making any network calls.
  Checks gate compatibility, qubit count limits, and shots limits before submitting.
  **Always run a dry-run before submitting.** A dry-run success followed by
  an actual submission failure is a critical bug — please report it.
- ``dry_run_batch`` — Validate multiple circuits offline.
- ``query_task`` — Query task status by ID.
- ``wait_for_result`` — Poll until a task completes or times out.
- ``list_tasks``, ``get_task``, ``save_task`` — Cache management.

CLI shortcut::

    uniqc submit circuit.originir --platform quafu --chip-id ScQ-P18 --dry-run

Python example::

    from uniqc.backend_adapter.task_manager import dry_run_task, submit_task
    from uniqc.circuit_builder import Circuit

    circuit = Circuit()
    circuit.h(0)
    circuit.measure(0)

    # Validate before submitting
    result = dry_run_task(circuit, backend='quafu', chip_id='ScQ-P18', shots=1000)
    if result.success:
        task_id = submit_task(circuit, backend='quafu', chip_id='ScQ-P18', shots=1000)
"""
