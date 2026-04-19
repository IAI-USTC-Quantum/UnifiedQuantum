#ifdef __GNUC__
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-value"
#endif

#include "pybind11/pybind11.h"
#include "pybind11/stl.h"
#include "pybind11/complex.h"
#include "pybind11/functional.h"
#include "pybind11/operators.h"

#include "simulator.h"
#include "density_operator_simulator.h"
#include "rng.h"
using namespace std;
using namespace pybind11::literals;
namespace py = pybind11;

PYBIND11_MODULE(uniqc_cpp, m)
{
	m.doc() = "[Module uniqc_cpp]";
	m.def("seed", &uniqc::seed);
	m.def("rand", &uniqc::rand);

	auto py_arg_global_controller = (py::arg("global_controller") = std::vector<size_t>{});
	auto py_arg_dagger = (py::arg("dagger") = false);

	using get_prob_type1 = uniqc::dtype(uniqc::StatevectorSimulator::*)(size_t, int);
	using get_prob_type2 = uniqc::dtype(uniqc::StatevectorSimulator::*)(const std::map<size_t, int>&);

	using pmeasure_type1 = std::vector<uniqc::dtype>(uniqc::StatevectorSimulator::*)(size_t);
	using pmeasure_type2 = std::vector<uniqc::dtype>(uniqc::StatevectorSimulator::*)(const std::vector<size_t>&);
	
	using measure_single_shot_type1 = size_t(uniqc::StatevectorSimulator::*)(size_t);
	using measure_single_shot_type2 = size_t(uniqc::StatevectorSimulator::*)(const std::vector<size_t>&);

	py::class_<uniqc::StatevectorSimulator>(m, "StatevectorSimulator")
		.def(py::init<>())
		.def_readwrite_static("max_qubit_num", &uniqc::StatevectorSimulator::max_qubit_num)
		.def_readonly("total_qubit", &uniqc::StatevectorSimulator::total_qubit)
		.def_readonly("state", &uniqc::StatevectorSimulator::state)
		.def("init_n_qubit", &uniqc::StatevectorSimulator::init_n_qubit)
		.def("hadamard", &uniqc::StatevectorSimulator::hadamard, py::arg("qn"), py_arg_global_controller, py_arg_dagger)
		.def("u22", &uniqc::StatevectorSimulator::u22, py::arg("qn"), py::arg("unitary"), py_arg_global_controller, py_arg_dagger)
		.def("x", &uniqc::StatevectorSimulator::x, py::arg("qn"), py_arg_global_controller, py_arg_dagger)
		.def("sx", &uniqc::StatevectorSimulator::sx, py::arg("qn"), py_arg_global_controller, py_arg_dagger)
		.def("y", &uniqc::StatevectorSimulator::y, py::arg("qn"), py_arg_global_controller, py_arg_dagger)
		.def("z", &uniqc::StatevectorSimulator::z, py::arg("qn"), py_arg_global_controller, py_arg_dagger)
		.def("s", &uniqc::StatevectorSimulator::s, py::arg("qn"), py_arg_global_controller, py_arg_dagger)
		.def("t", &uniqc::StatevectorSimulator::t, py::arg("qn"), py_arg_global_controller, py_arg_dagger)
		.def("cz", &uniqc::StatevectorSimulator::cz, py::arg("qn1"), py::arg("qn2"), py_arg_global_controller, py_arg_dagger)
		.def("iswap", &uniqc::StatevectorSimulator::iswap, py::arg("qn1"), py::arg("qn2"), py_arg_global_controller, py_arg_dagger)
		.def("swap", &uniqc::StatevectorSimulator::swap, py::arg("qn1"), py::arg("qn2"), py_arg_global_controller, py_arg_dagger)
		.def("xy", &uniqc::StatevectorSimulator::xy, py::arg("qn1"), py::arg("qn2"), py::arg("theta"), py_arg_global_controller, py_arg_dagger)
		.def("cnot", &uniqc::StatevectorSimulator::cnot, py::arg("controller"), py::arg("target"), py_arg_global_controller, py_arg_dagger)
		.def("rx", &uniqc::StatevectorSimulator::rx, py::arg("qn"), py::arg("theta"), py_arg_global_controller, py_arg_dagger)
		.def("ry", &uniqc::StatevectorSimulator::ry, py::arg("qn"), py::arg("theta"), py_arg_global_controller, py_arg_dagger)
		.def("rz", &uniqc::StatevectorSimulator::rz, py::arg("qn"), py::arg("theta"), py_arg_global_controller, py_arg_dagger)
		.def("u1", &uniqc::StatevectorSimulator::u1, py::arg("qn"), py::arg("theta"), py_arg_global_controller, py_arg_dagger)
		.def("u2", &uniqc::StatevectorSimulator::u2, py::arg("qn"), py::arg("phi"), py::arg("lamda"), py_arg_global_controller, py_arg_dagger)
		.def("rphi90", &uniqc::StatevectorSimulator::rphi90, py::arg("qn"), py::arg("phi"), py_arg_global_controller, py_arg_dagger)
		.def("rphi180", &uniqc::StatevectorSimulator::rphi180, py::arg("qn"), py::arg("phi"), py_arg_global_controller, py_arg_dagger)
		.def("rphi", &uniqc::StatevectorSimulator::rphi, py::arg("qn"), py::arg("theta"), py::arg("phi"), py_arg_global_controller, py_arg_dagger)
		.def("toffoli", &uniqc::StatevectorSimulator::toffoli, py::arg("controller1"), py::arg("controller2"), py::arg("target"), py_arg_global_controller, py_arg_dagger)
		.def("cswap", &uniqc::StatevectorSimulator::cswap, py::arg("controller"), py::arg("target1"), py::arg("target2"), py_arg_global_controller, py_arg_dagger)
		.def("xx", &uniqc::StatevectorSimulator::xx, py::arg("qn1"), py::arg("qn2"), py::arg("theta"), py_arg_global_controller, py_arg_dagger)
		.def("yy", &uniqc::StatevectorSimulator::yy, py::arg("qn1"), py::arg("qn2"), py::arg("theta"), py_arg_global_controller, py_arg_dagger)
		.def("zz", &uniqc::StatevectorSimulator::zz, py::arg("qn1"), py::arg("qn2"), py::arg("theta"), py_arg_global_controller, py_arg_dagger)
		.def("u3", &uniqc::StatevectorSimulator::u3, py::arg("qn"), py::arg("theta"), py::arg("phi"), py::arg("lamda"), py_arg_global_controller, py_arg_dagger)
		.def("phase2q", &uniqc::StatevectorSimulator::phase2q, py::arg("qn1"), py::arg("qn2"), py::arg("theta1"), py::arg("theta2"), py::arg("thetazz"), py_arg_global_controller, py_arg_dagger)
		.def("uu15", &uniqc::StatevectorSimulator::uu15, py::arg("qn1"), py::arg("qn2"), py::arg("parameters"), py_arg_global_controller, py_arg_dagger)
		
		.def("pauli_error_1q", &uniqc::StatevectorSimulator::pauli_error_1q, py::arg("qn"), py::arg("px"), py::arg("py"), py::arg("pz"))
		.def("depolarizing", &uniqc::StatevectorSimulator::depolarizing, py::arg("qn"), py::arg("p"))
		.def("bitflip", &uniqc::StatevectorSimulator::bitflip, py::arg("qn"), py::arg("p"))
		.def("phaseflip", &uniqc::StatevectorSimulator::phaseflip, py::arg("qn"), py::arg("p"))
		.def("pauli_error_2q", &uniqc::StatevectorSimulator::pauli_error_2q, py::arg("qn1"), py::arg("qn2"), py::arg("p"))
		.def("twoqubit_depolarizing", &uniqc::StatevectorSimulator::twoqubit_depolarizing, py::arg("qn1"), py::arg("qn2"), py::arg("p"))
		.def("kraus1q", &uniqc::StatevectorSimulator::kraus1q, py::arg("qn"), py::arg("kraus_ops"))
		.def("amplitude_damping", &uniqc::StatevectorSimulator::amplitude_damping, py::arg("qn"), py::arg("gamma"))

		.def("get_prob", (get_prob_type1)&uniqc::StatevectorSimulator::get_prob, py::arg("qn"), py::arg("qstate"))
		.def("get_prob", (get_prob_type2)&uniqc::StatevectorSimulator::get_prob, py::arg("measure_map"))
		.def("pmeasure", (pmeasure_type1)&uniqc::StatevectorSimulator::pmeasure, py::arg("qn"))
		.def("pmeasure", (pmeasure_type2)&uniqc::StatevectorSimulator::pmeasure, py::arg("measure_qubits"))
		
		.def("measure_single_shot", (measure_single_shot_type1)&uniqc::StatevectorSimulator::measure_single_shot, py::arg("qubit"))
		.def("measure_single_shot", (measure_single_shot_type2)&uniqc::StatevectorSimulator::measure_single_shot, py::arg("qubits"))
		;

	py::class_<uniqc::DensityOperatorSimulator>(m, "DensityOperatorSimulator")
		.def(py::init<>())
		.def_readwrite_static("max_qubit_num", &uniqc::DensityOperatorSimulator::max_qubit_num)
		.def_readonly("total_qubit", &uniqc::DensityOperatorSimulator::total_qubit)
		.def_readonly("state", &uniqc::DensityOperatorSimulator::state)
		.def("init_n_qubit", &uniqc::DensityOperatorSimulator::init_n_qubit)
		.def("hadamard", &uniqc::DensityOperatorSimulator::hadamard, py::arg("qn"), py_arg_global_controller, py_arg_dagger)
		.def("u22", &uniqc::DensityOperatorSimulator::u22, py::arg("qn"), py::arg("unitary"), py_arg_global_controller, py_arg_dagger)
		.def("x", &uniqc::DensityOperatorSimulator::x, py::arg("qn"), py_arg_global_controller, py_arg_dagger)
		.def("sx", &uniqc::DensityOperatorSimulator::sx, py::arg("qn"), py_arg_global_controller, py_arg_dagger)
		.def("y", &uniqc::DensityOperatorSimulator::y, py::arg("qn"), py_arg_global_controller, py_arg_dagger)
		.def("z", &uniqc::DensityOperatorSimulator::z, py::arg("qn"), py_arg_global_controller, py_arg_dagger)
		.def("s", &uniqc::DensityOperatorSimulator::s, py::arg("qn"), py_arg_global_controller, py_arg_dagger)
		.def("t", &uniqc::DensityOperatorSimulator::t, py::arg("qn"), py_arg_global_controller, py_arg_dagger)
		.def("cz", &uniqc::DensityOperatorSimulator::cz, py::arg("qn1"), py::arg("qn2"), py_arg_global_controller, py_arg_dagger)
		.def("iswap", &uniqc::DensityOperatorSimulator::iswap, py::arg("qn1"), py::arg("qn2"), py_arg_global_controller, py_arg_dagger)
		.def("swap", &uniqc::DensityOperatorSimulator::swap, py::arg("qn1"), py::arg("qn2"), py_arg_global_controller, py_arg_dagger)
		.def("xy", &uniqc::DensityOperatorSimulator::xy, py::arg("qn1"), py::arg("qn2"), py::arg("theta"), py_arg_global_controller, py_arg_dagger)
		.def("cnot", &uniqc::DensityOperatorSimulator::cnot, py::arg("controller"), py::arg("target"), py_arg_global_controller, py_arg_dagger)
		.def("rx", &uniqc::DensityOperatorSimulator::rx, py::arg("qn"), py::arg("theta"), py_arg_global_controller, py_arg_dagger)
		.def("ry", &uniqc::DensityOperatorSimulator::ry, py::arg("qn"), py::arg("theta"), py_arg_global_controller, py_arg_dagger)
		.def("rz", &uniqc::DensityOperatorSimulator::rz, py::arg("qn"), py::arg("theta"), py_arg_global_controller, py_arg_dagger)
		.def("u1", &uniqc::DensityOperatorSimulator::u1, py::arg("qn"), py::arg("theta"), py_arg_global_controller, py_arg_dagger)
		.def("u2", &uniqc::DensityOperatorSimulator::u2, py::arg("qn"), py::arg("phi"), py::arg("lamda"), py_arg_global_controller, py_arg_dagger)
		.def("rphi90", &uniqc::DensityOperatorSimulator::rphi90, py::arg("qn"), py::arg("phi"), py_arg_global_controller, py_arg_dagger)
		.def("rphi180", &uniqc::DensityOperatorSimulator::rphi180, py::arg("qn"), py::arg("phi"), py_arg_global_controller, py_arg_dagger)
		.def("rphi", &uniqc::DensityOperatorSimulator::rphi, py::arg("qn"), py::arg("theta"), py::arg("phi"), py_arg_global_controller, py_arg_dagger)
		.def("toffoli", &uniqc::DensityOperatorSimulator::toffoli, py::arg("controller1"), py::arg("controller2"), py::arg("target"), py_arg_global_controller, py_arg_dagger)
		.def("cswap", &uniqc::DensityOperatorSimulator::cswap, py::arg("controller"), py::arg("target1"), py::arg("target2"), py_arg_global_controller, py_arg_dagger)
		.def("xx", &uniqc::DensityOperatorSimulator::xx, py::arg("qn1"), py::arg("qn2"), py::arg("theta"), py_arg_global_controller, py_arg_dagger)
		.def("yy", &uniqc::DensityOperatorSimulator::yy, py::arg("qn1"), py::arg("qn2"), py::arg("theta"), py_arg_global_controller, py_arg_dagger)
		.def("zz", &uniqc::DensityOperatorSimulator::zz, py::arg("qn1"), py::arg("qn2"), py::arg("theta"), py_arg_global_controller, py_arg_dagger)
		.def("u3", &uniqc::DensityOperatorSimulator::u3, py::arg("qn"), py::arg("theta"), py::arg("phi"), py::arg("lamda"), py_arg_global_controller, py_arg_dagger)
		.def("phase2q", &uniqc::DensityOperatorSimulator::phase2q, py::arg("qn1"), py::arg("qn2"), py::arg("theta1"), py::arg("theta2"), py::arg("thetazz"), py_arg_global_controller, py_arg_dagger)
		.def("uu15", &uniqc::DensityOperatorSimulator::uu15, py::arg("qn1"), py::arg("qn2"), py::arg("parameters"), py_arg_global_controller, py_arg_dagger)
		
		.def("pauli_error_1q", &uniqc::DensityOperatorSimulator::pauli_error_1q, py::arg("qn"), py::arg("px"), py::arg("py"), py::arg("pz"))
		.def("depolarizing", &uniqc::DensityOperatorSimulator::depolarizing, py::arg("qn"), py::arg("p"))
		.def("bitflip", &uniqc::DensityOperatorSimulator::bitflip, py::arg("qn"), py::arg("p"))
		.def("phaseflip", &uniqc::DensityOperatorSimulator::phaseflip, py::arg("qn"), py::arg("p"))
		.def("pauli_error_2q", &uniqc::DensityOperatorSimulator::pauli_error_2q, py::arg("qn1"), py::arg("qn2"), py::arg("p"))
		.def("twoqubit_depolarizing", &uniqc::DensityOperatorSimulator::twoqubit_depolarizing, py::arg("qn1"), py::arg("qn2"), py::arg("p"))
		.def("kraus1q", &uniqc::DensityOperatorSimulator::kraus1q, py::arg("qn"), py::arg("kraus_ops"))
		.def("amplitude_damping", &uniqc::DensityOperatorSimulator::amplitude_damping, py::arg("qn"), py::arg("gamma"))
				
		.def("get_prob", &uniqc::DensityOperatorSimulator::get_prob)
		.def("get_prob", &uniqc::DensityOperatorSimulator::get_prob_map)
		.def("pmeasure", &uniqc::DensityOperatorSimulator::pmeasure)
		.def("pmeasure", &uniqc::DensityOperatorSimulator::pmeasure_list)
		.def("stateprob", &uniqc::DensityOperatorSimulator::stateprob)
		;
	
	/*py::enum_<uniqc::NoiseType>(m, "NoiseType")
		.value("Depolarizing", uniqc::NoiseType::Depolarizing)
		.value("Damping", uniqc::NoiseType::Damping)
		.value("BitFlip", uniqc::NoiseType::BitFlip)
		.value("PhaseFlip", uniqc::NoiseType::PhaseFlip)
		.value("TwoQubitDepolarizing", uniqc::NoiseType::TwoQubitDepolarizing)
		.export_values()
		;

	py::enum_<uniqc::UnitaryType>(m, "UnitaryType")
        .value("HADAMARD", uniqc::UnitaryType::HADAMARD)
        .value("IDENTITY", uniqc::UnitaryType::IDENTITY)
        .value("U22", uniqc::UnitaryType::U22)
        .value("X", uniqc::UnitaryType::X)
        .value("Y", uniqc::UnitaryType::Y)
		.value("Z", uniqc::UnitaryType::Z)
		.value("S", uniqc::UnitaryType::S)
		.value("T", uniqc::UnitaryType::T)
        .value("SX", uniqc::UnitaryType::SX)
        .value("CZ", uniqc::UnitaryType::CZ)
        .value("ISWAP", uniqc::UnitaryType::ISWAP)
        .value("XY", uniqc::UnitaryType::XY)
        .value("CNOT", uniqc::UnitaryType::CNOT)
        .value("RX", uniqc::UnitaryType::RX)
        .value("RY", uniqc::UnitaryType::RY)
        .value("RZ", uniqc::UnitaryType::RZ)
        .value("RPHI90", uniqc::UnitaryType::RPHI90)
        .value("RPHI180", uniqc::UnitaryType::RPHI180)
		.value("RPHI", uniqc::UnitaryType::RPHI)
		.value("TOFFOLI", uniqc::UnitaryType::TOFFOLI)
		.value("CSWAP", uniqc::UnitaryType::CSWAP)
        .export_values();*/

	//py::class_<uniqc::OpcodeType>(m, "OpcodeType")
	//	.def(py::init<uint32_t, 
 //                 const std::vector<size_t>&, 
 //                 const std::vector<double>&, 
 //                 bool, 
 //                 const std::vector<size_t>&>())
	//	.def_readwrite("op", &uniqc::OpcodeType::op)
	//	// There might be others
	//	;

	//using measure_shots_type1 = std::map<size_t, size_t> (uniqc::NoisySimulator::*)(const std::vector<size_t>&, size_t);
	//using measure_shots_type2 = std::map<size_t, size_t> (uniqc::NoisySimulator::*)(size_t);

	//
	//py::class_<uniqc::NoisySimulator>(m, "NoisySimulator")
	//	.def(py::init<size_t, 
 //                     const std::map<std::string, double>&, 
 //                     const std::vector<std::array<double, 2>>&>(),
	//		 py::arg("n_qubit"),
 //            py::arg("noise_description") = std::map<std::string, double>{},  // Default empty map
 //            py::arg("measurement_error") = std::vector<std::array<double, 2>>{}  // Default empty vector
 //       )
	//	.def_readonly("total_qubit", &uniqc::NoisySimulator::nqubit)
	//	.def_readonly("noise", &uniqc::NoisySimulator::noise)
	//	.def_readonly("measurement_error_matrices", &uniqc::NoisySimulator::measurement_error_matrices)
	//	.def("load_opcode", &uniqc::NoisySimulator::load_opcode)
	//	.def("insert_error", &uniqc::NoisySimulator::insert_error)	
	//	.def("get_measure_no_readout_error", &uniqc::NoisySimulator::get_measure_no_readout_error)
	//	.def("get_measure", &uniqc::NoisySimulator::get_measure)
	//	.def("measure_shots", (measure_shots_type1)&uniqc::NoisySimulator::measure_shots, py::arg("measure_qubits"), py::arg("shots"))
	//	.def("measure_shots", (measure_shots_type2)&uniqc::NoisySimulator::measure_shots, py::arg("shots"))
	//	
	//	.def("hadamard", &uniqc::NoisySimulator::hadamard, py::arg("qn"), py_arg_global_controller, py_arg_dagger)
	//	.def("u22", &uniqc::NoisySimulator::u22, py::arg("qn"), py::arg("unitary"), py_arg_global_controller, py_arg_dagger)
	//	.def("x", &uniqc::NoisySimulator::x, py::arg("qn"), py_arg_global_controller, py_arg_dagger)
	//	.def("sx", &uniqc::NoisySimulator::sx, py::arg("qn"), py_arg_global_controller, py_arg_dagger)
	//	.def("y", &uniqc::NoisySimulator::y, py::arg("qn"), py_arg_global_controller, py_arg_dagger)
	//	.def("z", &uniqc::NoisySimulator::z, py::arg("qn"), py_arg_global_controller, py_arg_dagger)
	//	.def("cz", &uniqc::NoisySimulator::cz, py::arg("qn1"), py::arg("qn2"), py_arg_global_controller, py_arg_dagger)
	//	.def("iswap", &uniqc::NoisySimulator::iswap, py::arg("qn1"), py::arg("qn2"), py_arg_global_controller, py_arg_dagger)
	//	.def("xy", &uniqc::NoisySimulator::xy, py::arg("qn1"), py::arg("qn2"), py::arg("theta"), py_arg_global_controller, py_arg_dagger)
	//	.def("cnot", &uniqc::NoisySimulator::cnot, py::arg("controller"), py::arg("target"), py_arg_global_controller, py_arg_dagger)
	//	.def("rx", &uniqc::NoisySimulator::rx, py::arg("qn"), py::arg("theta"), py_arg_global_controller, py_arg_dagger)
	//	.def("ry", &uniqc::NoisySimulator::ry, py::arg("qn"), py::arg("theta"), py_arg_global_controller, py_arg_dagger)
	//	.def("rz", &uniqc::NoisySimulator::rz, py::arg("qn"), py::arg("theta"), py_arg_global_controller, py_arg_dagger)
	//	.def("rphi90", &uniqc::NoisySimulator::rphi90, py::arg("qn"), py::arg("phi"), py_arg_global_controller, py_arg_dagger)
	//	.def("rphi180", &uniqc::NoisySimulator::rphi180, py::arg("qn"), py::arg("phi"), py_arg_global_controller, py_arg_dagger)
	//	.def("rphi", &uniqc::NoisySimulator::rphi, py::arg("qn"), py::arg("phi"), py::arg("theta"), py_arg_global_controller, py_arg_dagger)
	//	;

	//py::class_<uniqc::NoisySimulator_GateDependent, uniqc::NoisySimulator>(m, "NoisySimulator_GateDependent")
	//	.def(py::init<size_t,
	//			const std::map<std::string, double>&,
	//			const std::map<std::string, std::map<std::string, double>>&,
	//			const std::vector<std::array<double, 2>>&>(),
	//		py::arg("n_qubit"),
	//		py::arg("noise_description") = std::map<std::string, double>{},  // Default empty map
	//		py::arg("gate_noise_description") = std::map<std::string, std::map<std::string, double>>{},  // Default empty map
	//		py::arg("measurement_error") = std::vector<std::array<double, 2>>{}  // Default empty vector
	//	)
	//	;

	//py::class_<uniqc::NoisySimulator_GateSpecificError, uniqc::NoisySimulator>(m, "NoisySimulator_GateSpecificError")
	//	.def(py::init<size_t,
	//		const std::map<std::string, double>&,
	//		const uniqc::NoisySimulator_GateSpecificError::GateError1q_Description_t&,
	//		const uniqc::NoisySimulator_GateSpecificError::GateError2q_Description_t&,
	//		const std::vector<std::array<double, 2>>&>(),
	//		py::arg("n_qubit"),
	//		py::arg("noise_description") = std::map<std::string, double>{},  // Default empty map
	//		py::arg("gate_error1q_description") = uniqc::NoisySimulator_GateSpecificError::GateError1q_Description_t{},  // Default empty map
	//		py::arg("gate_error2q_description") = uniqc::NoisySimulator_GateSpecificError::GateError2q_Description_t{},  // Default empty map
	//		py::arg("measurement_error") = std::vector<std::array<double, 2>>{}  // Default empty vector
	//	)
	//	;
}

#ifdef __GNUC__
#pragma GCC diagnostic pop
#endif