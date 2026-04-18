import pytest

from uniq.circuit_builder.qasm_spec import generate_sub_gateset_qasm
from uniq.qasm import OpenQASM2_BaseParser
import uniq.simulator as qsim
import numpy as np

from uniq.circuit_builder.random_qasm import random_qasm, available_qasm_gates
from uniq.simulator.originir_simulator import OriginIR_Simulator
from uniq.simulator.qasm_simulator import QASM_Simulator
from uniq.circuit_builder import Circuit
from uniq.test._utils import uniq_test, NotMatchError

@pytest.mark.xfail(reason="QASM parser doesn't support if statements from qiskit transpiler output")
@uniq_test('Test QASM Parser')
def run_test_qasm_parser():
    # Generate random OriginIR circuit, and parse it
    n_qubits = 5
    n_gates = 50
    n_test = 50
    for i in range(n_test):
        
        gate_set = ['h', 'cx', 'rx', 'ry', 'rz', 
                    'u1', 'u2', 'u3', 'id', 'x', 'y', 'z', 
                    's', 'sdg', 't', 'tdg', 'swap'  
                    'ccx', 'cu1', 'cswap']        

        gate_set = ['h', 'cx', 'rx', 'ry', 'rz', 
                    'u1', 'u2', 'u3', 'id', 'x', 'y', 'z', 
                    's', 'sdg', 't', 'tdg', 'swap' 
                    'ccx', 'cu1', 'cswap']
        
        gate_set = generate_sub_gateset_qasm(gate_set)

        qasm_1 = random_qasm(n_qubits, n_gates, instruction_set=gate_set, measurements=True)
        parser = OpenQASM2_BaseParser()
        parser.parse(qasm_1)
        circuit_obj : Circuit = parser.to_circuit()
        oir_1 = circuit_obj.originir

        # simulate oir_1 and oir_2
        sim_oir = OriginIR_Simulator(backend_type='statevector')
        sim_qasm = QASM_Simulator(backend_type='statevector', least_qubit_remapping=True)
        
        state_1 = sim_oir.simulate_pmeasure(oir_1)
        state_2 = sim_qasm.simulate_pmeasure(qasm_1)

        # compare the results
        if not np.allclose(state_1, state_2):
            raise NotMatchError(
            '---------------\n'
            f'OriginIR =\n {oir_1}\n'
            f'QASM =\n {qasm_1}\n'
            '---------------\n'
            'Result not match!\n'
            f'Reference = {state_1}\n'
            f'My Result = {state_2}\n'
        )
        print(f'Test {i+1} passed.')


if __name__ == '__main__':
    run_test_qasm_parser()