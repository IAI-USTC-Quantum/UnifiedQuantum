import hashlib
import pickle
from pathlib import Path

import numpy as np
import pytest
import qiskit
import qiskit.qasm2 as qasm
from qiskit import transpile
from qiskit_aer import AerSimulator

from uniqc.compile.qasm import NotSupportedGateError, OpenQASM2_BaseParser
from uniqc.simulator import Simulator
from uniqc.test._utils import NotMatchError, uniq_test

QASMBENCH_SHA256 = "b3b44b9fd207921eeeae54c1cdfcad04a546e368765b045a40bc0ff542feefed"


def _load_QASMBench(path):
    """Load a pickle accepted only as trusted, immutable repository test data."""
    path = Path(path)
    filename = path / "QASMBench.pkl"

    with open(filename, "rb") as fp:
        payload = fp.read()

    digest = hashlib.sha256(payload).hexdigest()
    if digest != QASMBENCH_SHA256:
        raise ValueError(f"QASMBench.pkl SHA-256 mismatch: expected {QASMBENCH_SHA256}, got {digest}")

    return pickle.loads(payload)


def test_qasmbench_digest_mismatch_does_not_unpickle(tmp_path, monkeypatch):
    fixture = tmp_path / "QASMBench.pkl"
    fixture.write_bytes(b"benign digest mismatch")

    def fail_if_called(_payload):
        pytest.fail("pickle.loads must not be called when the fixture digest mismatches")

    monkeypatch.setattr(pickle, "loads", fail_if_called)

    with pytest.raises(ValueError, match="QASMBench.pkl SHA-256 mismatch"):
        _load_QASMBench(tmp_path)


def _transpile_circuit(qc):
    # Use the Aer simulator
    backend = AerSimulator()
    try:
        quantum_circuit = qasm.loads(qc)
        # Transpile the circuit for the backend
        transpiled_qc = transpile(quantum_circuit, backend=backend, optimization_level=0)

        qasm_circuit = qasm.dumps(transpiled_qc)
        return qasm_circuit
    except Exception as e:
        print("Error transpiling circuit: ", qc)
        raise e


def _reference_result_to_array(result):
    for key in result:
        n_qubit = len(key)
        break

    result_list = np.zeros(2**n_qubit)
    for key in result:
        index = int(key, base=2)
        result_list[index] = result[key]

    return result_list


def _check_result(transpiled_circuit, reference_result, backend_type):

    reference_array = _reference_result_to_array(reference_result)

    # print('Testing circuit: ', transpiled_circuit)
    # print('Reference Result: ', reference_result)
    qasm_simulator = Simulator(backend_type, least_qubit_remapping=False)
    my_result = qasm_simulator.simulate_stateprob(transpiled_circuit)

    if len(reference_array) != len(my_result):
        print("---------------")
        print(transpiled_circuit)
        print(reference_result)
        print("---------------")
        raise NotMatchError(f"Size not match!\nReference = {reference_array}\nMy Result = {my_result}\n")
    try:
        v = np.allclose(reference_array, my_result)
    except Exception as e:
        error_message = (
            "---------------\n"
            "Unexpected error occurred!!!\n"
            f"Transpiled Circuit: {transpiled_circuit}\n"
            f"Reference Result: {reference_result}\n"
            "---------------\n"
            f"The exception is: {str(e)}\n"
        )
        e.args = (error_message,) + e.args
        raise e

    if not np.allclose(reference_array, my_result):
        raise NotMatchError(
            "---------------\n"
            f"{transpiled_circuit}\n"
            f"{reference_result}\n"
            "---------------\n"
            "Result not match!\n"
            f"Reference = {reference_array}\n"
            f"My Result = {my_result}\n"
        )

    print("Test passed!")


def test_qasm(path="./uniqc/test"):
    dataset = _load_QASMBench(path)
    # print(dataset)
    # print(len(dataset))

    count_passed = 0
    passed_list = []
    count_not_supported = 0
    not_supported_list = []
    for circuit in dataset:
        try:
            transpiled_circuit = _transpile_circuit(circuit)
        except qiskit.qasm2.exceptions.QASM2ExportError:
            print("Error transpiling circuit:", circuit)
            # skip this circuit
            continue

        parser = OpenQASM2_BaseParser()
        try:
            # print('-- Parse --')
            # print(transpiled_circuit)
            parser.parse(transpiled_circuit)
            print("-- Parse OK --")
            # print(parser.formatted_qasm)
            count_passed += 1
            passed_list.append(circuit)
        except NotSupportedGateError:
            count_not_supported += 1
            not_supported_list.append(circuit)
        except Exception as e:
            raise e

    print(count_passed, "circuits passed")
    print(count_not_supported, "circuits not supported")
    # print(passed_list)
    # print(not_supported_list)

    err_list = []
    for circuit in passed_list:
        try:
            transpiled_circuit = _transpile_circuit(circuit)
            _check_result(transpiled_circuit, dataset[circuit], "statevector")
            _check_result(transpiled_circuit, dataset[circuit], "density_operator")
        except NotMatchError as e:
            print("Test Failed!")
            err_list.append(e)

    if not err_list:
        print("All circuits passed!")
        return

    for i, e in enumerate(err_list):
        print("Circuit", i, "failed:", e)

    print(len(err_list), "circuits failed")
    print(len(passed_list) - len(err_list), "circuits passed")

    raise ValueError("Some circuits failed!")


@uniq_test("Test QASMBench")
def run_test_qasm():
    test_qasm()


if __name__ == "__main__":
    test_qasm()
