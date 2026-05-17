# Test suite for uniqc


def run_test():
    """Run all tests. Imports are placed inside to avoid blocking pytest collection."""
    from .benchmark.test_QASMBench import run_test_qasm
    from .cloud.test_demos import run_test_demos
    from .cloud.test_result_adapter import run_test_result_adapter
    from .core.test_general import run_test_general
    from .core.test_originir_parser import run_test_originir_parser
    from .core.test_qasm_parser import run_test_qasm_parser
    from .simulator.test_random_OriginIR import run_test_random_originir_density_operator
    from .simulator.test_random_QASM import (
        run_test_random_qasm_density_operator,
        run_test_random_qasm_density_operator_compare_with_qutip,
        run_test_random_qasm_density_operator_qutip,
        run_test_random_qasm_statevector,
    )
    from .simulator.test_random_QASM_measure import run_test_random_qasm_compare_shots
    from .simulator.test_simulator import run_test_simulator

    run_test_general()
    run_test_demos()
    run_test_simulator()
    run_test_originir_parser()
    run_test_qasm_parser()
    run_test_result_adapter()
    run_test_qasm()
    run_test_random_qasm_statevector()
    run_test_random_qasm_density_operator()
    run_test_random_qasm_density_operator_qutip()
    run_test_random_qasm_density_operator_compare_with_qutip()
    run_test_random_originir_density_operator()
    run_test_random_qasm_compare_shots()

    print("All tests passed~!!!")
