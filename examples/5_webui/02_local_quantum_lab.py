"""02 — Independent local quantum lab

[doc-require: cpp]
[doc-output-include: stdout, source]

The CLI and browser use these same local presets and the existing native
simulation path. Only exact probabilities and analytic errors are printed;
wall time is deliberately omitted from this deterministic example.
"""

from uniqc.gateway.demo import DemoRequest, run_demo


def main():
    for case in ("ghz", "w", "ramsey"):
        result = run_demo(DemoRequest(case=case, qubits=3, phase=0.73))
        assert result["max_probability_error"] < 1e-10
        print(case, "probability sum:", f"{result['probability_sum']:.10f}")
        print("analytic error < 1e-10:", result["max_probability_error"] < 1e-10)


if __name__ == "__main__":
    main()
