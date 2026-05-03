import numpy as np
from uniqc.simulator.qasm_simulator import QASM_Simulator
from uniqc.test._utils import uniq_test, NotMatchError
from uniqc.compile.qasm import NotSupportedGateError
from uniqc.circuit_builder.random_qasm import random_qasm
from uniqc.circuit_builder.qasm_spec import available_qasm_gates, generate_sub_gateset_qasm

import qiskit
import qiskit.qasm2 as qasm
from qiskit.circuit import library as lib
from qiskit.qasm2.parse import CustomInstruction, LEGACY_CUSTOM_INSTRUCTIONS
from qiskit_aer import AerSimulator
from qiskit import transpile
from qiskit_aer import Aer

def simulate_by_qiskit_statevector(qasm_str):
    '''Simulate the circuit by qiskit statevector simulator.

    Args:
        qasm_str (str): The QASM code to be simulated.

    Returns:
        numpy.ndarray: The probability of each state.

    Note:
        Measure operations are removed from the circuit before simulation.
    '''
    qc = qasm.loads(qasm_str, custom_instructions=LEGACY_CUSTOM_INSTRUCTIONS)
    for op in qc.data[:]:
        if op.operation.name == 'measure':
            qc.data.remove(op)

    backend = Aer.get_backend("statevector_simulator")

    # get probabilites of all states from AerSimulator
    result = backend.run(qc).result()
    statevector = result.get_statevector(qc).data

    problist = np.abs(statevector)**2
    return problist


def _check_result(transpiled_circuit, reference_array, backend_type):

    qasm_simulator = QASM_Simulator(backend_type)
    my_result = qasm_simulator.simulate_pmeasure(transpiled_circuit)

    if len(reference_array) != len(my_result):
        print('---------------')
        print(transpiled_circuit)
        print(reference_array)
        print('---------------')
        raise NotMatchError('Size not match!\n'
                        'Reference = {}\n'
                        'My Result = {}\n'.format(reference_array, my_result))
    try:
        v = np.allclose(reference_array, my_result)
    except Exception as e:       
        error_message = (
            '---------------\n'
            'Unexpected error occurred!!!\n'
            f'Transpiled Circuit: {transpiled_circuit}\n'
            f'Reference Result: {reference_array}\n'
            '---------------\n'
            f'The exception is: {str(e)}\n'
        )
        e.args = (error_message,) + e.args
        raise e
        
    if not np.allclose(reference_array, my_result):            
        raise NotMatchError(
            '---------------\n'
            f'{transpiled_circuit}\n'
            f'{reference_array}\n'
            '---------------\n'
            'Result not match!\n'
            f'Reference = {reference_array}\n'
            f'My Result = {my_result}\n'
        )



def _test_random_qasm(circuit, backend_type):
    # simulate via qiskit
    qiskit_result = simulate_by_qiskit_statevector(circuit)

    # check result
    try:
        _check_result(circuit, qiskit_result, backend_type)
        return None
    except NotMatchError as e:
        return e
    except Exception as e:
        # other unexpected error
        raise e

def _test_random_qasm_batch(
    random_batchsize = 100, 
    n_qubit = 5,
    n_gates = 20,
    instruction_set = available_qasm_gates, 
    backend_type = 'statevector'):

    err_list = []
    passed_count = 0

    for i in range(random_batchsize):

        qasm_code = random_qasm(n_qubits=n_qubit,
                                n_gates=n_gates,
                                instruction_set=instruction_set)
        err = _test_random_qasm(qasm_code, backend_type)
        if err:
            print(f'Test failed! Error: {err}')
            err_list.append(err)
        else:
            print('Test passed!')
            passed_count += 1


    print(len(err_list), 'circuits failed')
    print(passed_count, 'circuits passed')

    if len(err_list) > 0:
        raise ValueError('Some circuits failed!')


@uniq_test('Test Random QASM Statevector')
def run_test_random_qasm_statevector():

    gate_set = ['h', 'cx', 'rx', 'ry', 'rz', 
                'u1', 'u2', 'u3', 'id', 'x', 'y', 'z', 
                's', 'sdg', 't', 'tdg', 'swap', 
                'ccx', 'cu1', 'cswap']
    gate_set = generate_sub_gateset_qasm(gate_set)

    _test_random_qasm_batch(random_batchsize=100, 
                           n_qubit=5, n_gates=50, 
                           instruction_set=gate_set,
                           backend_type='statevector')


@uniq_test('Test Random QASM Density Operator')
def run_test_random_qasm_density_operator():
    
    gate_set = ['h', 'cx', 'rx', 'ry', 'rz', 
                'u1', 'u2', 'u3', 'id', 'x', 'y', 'z', 
                's', 'sdg', 't', 'tdg', 'swap', 
                'ccx', 'cu1', 'cswap']

    gate_set = ['h', 'cx', 'rx', 'ry', 'rz', 
                'u1', 'u2', 'u3', 'id', 'x', 'y', 'z', 
                's', 'sdg', 't', 'tdg', 'swap', 
                'ccx', 'cu1', 'cswap']
    gate_set = generate_sub_gateset_qasm(gate_set)

    _test_random_qasm_batch(random_batchsize=100, 
                           n_qubit=5, n_gates=50, 
                           instruction_set=gate_set,
                           backend_type='density_operator')

@uniq_test('Test Random QASM Density Operator (Qutip)')
def run_test_random_qasm_density_operator_qutip():
    
    gate_set = ['h', 'cx', 'rx', 'ry', 'rz', 
                'u1', 'u2', 'u3', 'id', 'x', 'y', 'z', 
                's', 'sdg', 't', 'tdg', 'swap', 
                'ccx', 'cu1', 'cswap']
    gate_set = ['h', 'cx', 'rx', 'ry', 'rz', 
                'u1', 'u2', 'u3', 'id', 'x', 'y', 'z', 
                's', 'sdg', 't', 'tdg', 'swap', 
                'ccx', 'cu1', 'cswap']
    gate_set = generate_sub_gateset_qasm(gate_set)

    _test_random_qasm_batch(random_batchsize=100, 
                           n_qubit=5, n_gates=50, 
                           instruction_set=gate_set,
                           backend_type='density_operator_qutip')


def compare_density_operator(circuit):
    # This test compares two density operators generated by QuTip and UnifiedQuantum.
    # The test is based on the following steps:
    # 1. Simulate the circuit using QuTip and UnifiedQuantum.
    # 2. Compare the results.
    # 3. If the results are not the same, raise an error.

    # Step 1: Simulate the circuit using QuTip and UnifiedQuantum
    sim_uniq = QASM_Simulator(backend_type='density_operator')
    sim_qutip = QASM_Simulator(backend_type='density_operator_qutip')

    mat_uniq = sim_uniq.simulate_density_matrix(circuit)
    mat_qutip = sim_qutip.simulate_density_matrix(circuit)
    # Step 2: Compare the results
    if not np.allclose(mat_uniq, mat_qutip):
        return NotMatchError(
            '---------------\n'
            f'{circuit}\n'
            '---------------\n'
            'Result not match!\n'
            f'UnifiedQuantum Result = {mat_uniq}\n'
            f'QuTip Result = {mat_qutip}\n'
        )
    
def test_random_qasm_compare_density_operator(
        random_batchsize = 100, 
        n_qubit = 5,
        n_gates = 20,
        instruction_set = available_qasm_gates):
    
    err_list = []
    passed_count = 0
    for i in range(random_batchsize):
        qasm_code = random_qasm(n_qubits=n_qubit,
                                n_gates=n_gates,
                                instruction_set=instruction_set)
        
        err = compare_density_operator(qasm_code)    
        
        if err:
            print(f'Test failed! Error: {err}')
            err_list.append(err)
        else:
            print('Test passed!')
            passed_count += 1


    print(len(err_list), 'circuits failed')
    print(passed_count, 'circuits passed')

    if len(err_list) > 0:
        raise ValueError('Some circuits failed!')
    
@uniq_test('Test Random QASM Density Operator (Compare with QuTip)')
def run_test_random_qasm_density_operator_compare_with_qutip():
    
    gate_set = ['h', 'cx', 'rx', 'ry', 'rz', 
                'u1', 'u2', 'u3', 'id', 'x', 'y', 'z', 
                's', 'sdg', 't', 'tdg', 'swap', 
                'ccx', 'cu1', 'cswap']
    
    gate_set = ['h', 'cx',  'rx', 'ry', 'rz', 
                'u1', 'u2', 'u3', 'id', 'x', 'y', 'z', 
               's', 'sdg', 't', 'tdg', 'swap', 
                'ccx', 'cu1', 'cswap']
    
    gate_set = generate_sub_gateset_qasm(gate_set)
    test_random_qasm_compare_density_operator(
        random_batchsize=100, 
        n_qubit=5, n_gates=50,
        instruction_set=gate_set)

if __name__ == '__main__':
    run_test_random_qasm_statevector()
    run_test_random_qasm_density_operator()
    run_test_random_qasm_density_operator_qutip()
    run_test_random_qasm_density_operator_compare_with_qutip()
