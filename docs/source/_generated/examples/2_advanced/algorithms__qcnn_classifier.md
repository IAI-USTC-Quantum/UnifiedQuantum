### QCNN Quantum State Classifier using TorchQuantum backend.

*Source*: ``examples/2_advanced/algorithms/qcnn_classifier.py``  
*Status*: **pass**

Demonstrates a Quantum Convolutional Neural Network for classifying
quantum states (GHZ vs product states) with native PyTorch autograd.

**Source code**

```{literalinclude} ../../../examples/2_advanced/algorithms/qcnn_classifier.py
:language: python
```

**Stdout**

```text
============================================================
QCNN State Classifier — TorchQuantum Backend
============================================================

Task: Classify GHZ vs |0...0> states
Qubits: 4
Model: QCNN

Parameters: 9

  Epoch  10 | Loss: 0.2731 | Acc: 0.5000
  Epoch  20 | Loss: 0.2550 | Acc: 0.5000
  Epoch  30 | Loss: 0.2543 | Acc: 0.1000
  Epoch  40 | Loss: 0.2542 | Acc: 0.1000
  Epoch  50 | Loss: 0.2541 | Acc: 0.1000

Training complete.
```

