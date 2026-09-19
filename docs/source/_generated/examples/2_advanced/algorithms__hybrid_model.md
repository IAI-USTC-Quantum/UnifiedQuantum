### Hybrid Classical-Quantum Model using TorchQuantum backend.

*Source*: ``examples/2_advanced/algorithms/hybrid_model.py``  
*Status*: **pass**

Demonstrates a hybrid architecture: Classical encoder → Quantum circuit
→ Classical decoder, for 2D binary classification.

**Source code**

```{literalinclude} ../../../examples/2_advanced/algorithms/hybrid_model.py
:language: python
```

**Stdout**

```text
============================================================
Hybrid Classical-Quantum Model — TorchQuantum Backend
============================================================

Dataset: make_moons (100 samples)
Model: HybridQCLModel (classical → quantum → classical)
Total parameters: 181
  Encoder:  116
  Quantum:  16
  Decoder:  49

  Epoch  10 | Loss: 0.5884 | Acc: 0.9000
  Epoch  20 | Loss: 0.4061 | Acc: 0.8800
  Epoch  30 | Loss: 0.2890 | Acc: 0.8900
  Epoch  40 | Loss: 0.2096 | Acc: 0.9200
  Epoch  50 | Loss: 0.1276 | Acc: 0.9700

Final accuracy: 0.9800
```

