### 量子体积与本地编译/执行吞吐基准

*Source*: ``examples/2_advanced/09_benchmark_qv_throughput.py``  
*Status*: **pass**

Quantum Volume and local compile/execute throughput benchmark entries.

Demonstrates the two NISQ-framework benchmark entries added this round:

* Quantum Volume (Cross et al. 2019) — seeded model circuits, heavy-output
  judgement, QV = 2**width on success.
* Local compile/execute throughput — circuits/hour at a fixed
  shots-per-circuit budget, with the timing boundary recorded in the report.

Both entries run entirely on the local simulator stack (no cloud task).

Usage:
    python 09_benchmark_qv_throughput.py

**Source code**

```{literalinclude} ../../../examples/2_advanced/09_benchmark_qv_throughput.py
:language: python
```

**Stdout**

```text
== Quantum Volume (width=4, trials=5, shots=500, seed=7) ==
mean heavy-output probability : 0.8296 +/- 0.0075
trials passed                 : 5/5
criterion mean_h - 2*sigma > 2/3 : PASS
Quantum Volume                : 16

== Local compile/execute throughput (100 circuits x 8q depth 6, 1000 shots) ==
compile   : 0.323s (1,113,327 circuits/h)
execute   : 0.046s (7,865,866 circuits/h)
total     : 0.369s -> 975,286 circuits/h
>= 30,000 circuits/hour        : PASS
timing boundary               : circuits/hour >= 30000 at the configured shots-per-circuit; boundary = OriginIR parse/preprocess + statevector simulate + shot sampling
cpu backend                   : uniqc_cpp.StatevectorSimulator (via uniqc.Simulator)
```

