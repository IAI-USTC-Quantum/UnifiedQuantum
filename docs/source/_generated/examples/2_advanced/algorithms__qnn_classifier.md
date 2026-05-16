### QNN Binary Classifier using TorchQuantum backend.

*Source*: ``examples/2_advanced/algorithms/qnn_classifier.py``  
*Status*: **pass**

Demonstrates a Quantum Neural Network for binary classification on
a synthetic moons dataset with native PyTorch autograd.

**Source code**

```{literalinclude} ../../../examples/2_advanced/algorithms/qnn_classifier.py
:language: python
```

**Stdout**

```text
============================================================
QNN Binary Classifier — TorchQuantum Backend
============================================================

Dataset: make_moons (100 samples, 2 features)
Model: QNN (n_qubits=4, depth=2)
Parameters: 16

  Epoch  10 | Loss: 1.0679 | Acc: 0.5000
  Epoch  20 | Loss: 0.9206 | Acc: 0.5100
  Epoch  30 | Loss: 0.8185 | Acc: 0.5100
  Epoch  40 | Loss: 0.7491 | Acc: 0.5300
  Epoch  50 | Loss: 0.7014 | Acc: 0.5800

Final accuracy: 0.5800
```

