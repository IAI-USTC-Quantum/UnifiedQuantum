"""Demo tests using the unified task API."""

import math

from uniqc import Circuit, calculate_expectation, submit_task, wait_for_result
from uniqc.test._utils import uniq_test


def _build_circuit():
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
    """Demo 2: Submit task using dummy mode."""
    circuit = _build_circuit()

    # Submit with dummy backend for local simulation
    task_id = submit_task(circuit, backend='dummy', shots=1000)
    print(f"Task ID: {task_id}")

    # Wait for result (immediate for dummy mode)
    result = wait_for_result(task_id, timeout=60)

    if result:
        print(f"Counts: {result.get('counts', {})}")
        print(f"Probabilities: {result.get('probabilities', {})}")


def demo_3():
    """Demo 3: Result post-processing with expectation values."""
    circuit = _build_circuit()

    # Submit with dummy mode
    task_id = submit_task(circuit, backend='dummy', shots=1000)
    result = wait_for_result(task_id, timeout=60)

    if result:
        probs = result.get('probabilities', {})
        print(f"Probabilities: {probs}")

        # Calculate expectation values using probabilities
        # Note: circuit uses 4 qubits (0-3), so Hamiltonians must be 4-qubit strings
        if probs:
            exps = [
                calculate_expectation(probs, h)
                for h in ['ZIII', 'IIIZ']
            ]
            print(f"<ZIII> = {exps[0]}")
            print(f"<IIIZ> = {exps[1]}")


@uniq_test('Test Demos')
def run_test_demos():
    demo_2()
    demo_3()


if __name__ == '__main__':
    run_test_demos()
