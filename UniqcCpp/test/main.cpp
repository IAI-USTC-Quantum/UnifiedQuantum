#include "basic_math.h"
#include "density_operator_simulator.h"
#include "simulator.h"

#include <cmath>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <vector>

int main() {
    try {
        if (uniqc::extract_digit(0b1010, 1) != 1 ||
            uniqc::extract_digits(0b1101, {0, 1, 3}) != 0b101 ||
            !uniqc::float_equal(uniqc::abs_sqr({0.0, 1.0}), 1.0) ||
            !uniqc::_assert_u22(uniqc::pauli_x)) {
            std::cerr << "basic math smoke checks failed\n";
            return 1;
        }

        uniqc::StatevectorSimulator statevector;
        statevector.init_n_qubit(2);
        statevector.hadamard(0);
        statevector.cnot(0, 1);

        const auto probabilities = statevector.pmeasure({0, 1});
        if (probabilities.size() != 4) {
            std::cerr << "unexpected probability vector size\n";
            return 1;
        }
        if (std::abs(probabilities[0] - 0.5) > uniqc::eps ||
            std::abs(probabilities[1]) > uniqc::eps ||
            std::abs(probabilities[2]) > uniqc::eps ||
            std::abs(probabilities[3] - 0.5) > uniqc::eps) {
            std::cerr << "Bell-state probabilities are incorrect\n";
            return 1;
        }

        uniqc::DensityOperatorSimulator density_operator;
        density_operator.init_n_qubit(1);
        density_operator.hadamard(0);
        const auto density_probabilities = density_operator.stateprob();
        if (density_probabilities.size() != 2 ||
            std::abs(density_probabilities[0] - 0.5) > uniqc::eps ||
            std::abs(density_probabilities[1] - 0.5) > uniqc::eps) {
            std::cerr << "density-operator probabilities are incorrect\n";
            return 1;
        }

        // uu15 must reject parameter vectors that are not exactly 15-sized
        // instead of indexing out of bounds.
        bool uu15_threw = false;
        try {
            statevector.uu15(0, 1, std::vector<double>(14, 0.0));
        } catch (const std::invalid_argument&) {
            uu15_threw = true;
        }
        if (!uu15_threw) {
            std::cerr << "StatevectorSimulator::uu15 accepted a wrong-sized parameter vector\n";
            return 1;
        }
        uu15_threw = false;
        uniqc::DensityOperatorSimulator density_operator_2q;
        density_operator_2q.init_n_qubit(2);
        try {
            density_operator_2q.uu15(0, 1, std::vector<double>(16, 0.0));
        } catch (const std::invalid_argument&) {
            uu15_threw = true;
        }
        if (!uu15_threw) {
            std::cerr << "DensityOperatorSimulator::uu15 accepted a wrong-sized parameter vector\n";
            return 1;
        }

        std::cout << "UnifiedQuantum C++ smoke test passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "smoke test failed: " << error.what() << '\n';
        return 2;
    }
}
