'''This is the demo for UnifiedQuantum

# 2. Run in Dummy Mode

## Concepts:

    Dummy mode: a mode that produces locally simulated results instead of
    sending them to real quantum cloud platforms. This is used to test
    your program before real task submission.

## Unified API

    UnifiedQuantum provides a unified interface for submitting tasks to
    different quantum backends (OriginQ, Quafu, IBM). Simply change the
    'backend' parameter to switch platforms.

## Enabling Dummy Mode

    Use a backend name prefixed with ``dummy`` to activate local simulation:

        - ``dummy`` — default simulator
        - ``dummy:originq:WK_C180`` — simulator with chip characterization

'''

import math
from uniqc import Circuit, submit_task, wait_for_result, query_task


def build_circuit():
    """Build a simple quantum circuit."""
    c = Circuit()
    c.x(0)
    c.rx(1, math.pi)
    c.ry(2, math.pi / 2)
    c.cnot(2, 3)
    c.cz(1, 2)
    c.measure(0, 1, 2)
    return c


def demo_2():
    """Demonstrate dummy mode task submission."""
    # Build circuit
    circuit = build_circuit()

    # Submit task with dummy backend for local simulation
    # This works without any real cloud platform configuration
    task_id = submit_task(
        circuit,
        backend='dummy',
        shots=1000,
    )

    print(f"Task ID: {task_id}")

    # Wait for result (immediate for dummy mode)
    result = wait_for_result(task_id, backend='dummy', timeout=60)

    if result:
        print(f"Status: success")
        print(f"Counts: {result.get('counts', {})}")
        print(f"Probabilities: {result.get('probabilities', {})}")
    else:
        print("Task did not complete")

    # Query task status
    task_info = query_task(task_id, backend='dummy')
    print(f"Task status: {task_info.status}")


if __name__ == '__main__':
    demo_2()
