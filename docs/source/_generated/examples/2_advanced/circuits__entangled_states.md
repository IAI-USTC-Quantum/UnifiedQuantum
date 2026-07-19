### Entangled State Preparation — GHZ, W, and Cluster states.

*Source*: ``examples/2_advanced/circuits/entangled_states.py``  
*Status*: **pass**

Demonstrates:
  * Preparing GHZ, W, and Cluster entangled states
  * Measuring and displaying probability distributions
  * Using the entangled_states module from uniqc

Usage:
    python entangled_states.py --state [ghz|w|cluster] [--n-qubits N] [--shots N]

References:
    * GHZ: Greenberger, D. M., Horne, M. A. & Zeilinger, A. (1989).
      "Going Beyond Bell's Theorem." In Bell's Theorem, Quantum Theory
      and Conceptions of the Universe, 69–72.
    * W state: Dür, W., Vidal, G. & Cirac, J. I. (2000).
      "Three qubits can be entangled in two inequivalent ways."
      Physical Review A, 62(6), 062314.
    * Cluster: Briegel, H. J. & Raussendorf, R. (2001).
      "Persistent Entanglement in Arrays of Interacting Particles."
      Physical Review Letters, 86(5), 910.

**Source code**

```{literalinclude} ../../../examples/2_advanced/circuits/entangled_states.py
:language: python
```

**Stdout**

```text
 GHZ State — 4 qubits

 Probability distribution:
   |0000⟩: 0.4944 ████████████████████████
   |1111⟩: 0.5056 █████████████████████████

 Dominant basis states (2):
   |1111⟩: 0.5056
   |0000⟩: 0.4944
```

