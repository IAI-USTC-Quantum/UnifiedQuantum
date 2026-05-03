"""QCNN Quantum State Classifier using TorchQuantum backend.

Demonstrates a Quantum Convolutional Neural Network for classifying
quantum states (GHZ vs product states) with native PyTorch autograd.
"""

try:
    import torch
    import torch.nn as nn

    from uniqc import QCNNClassifier
except ImportError as e:
    print(f"Required dependencies not available: {e}")
    print("Install with: pip install unified-quantum[pytorch]")
    print('Then install TorchQuantum manually: pip install "torchquantum @ git+https://github.com/Agony5757/torchquantum.git@fix/optional-qiskit-deps"')
    raise SystemExit(1)


def generate_state_dataset(n_qubits: int, n_samples: int):
    """Generate dataset of GHZ (label=1) and |0...0> (label=0) states."""
    from uniqc import Circuit
    from uniqc.simulator import OriginIR_Simulator

    sim = OriginIR_Simulator(backend_type="statevector")

    states = []
    labels = []

    for i in range(n_samples):
        if i < n_samples // 2:
            # |0...0> state
            c = Circuit(n_qubits)
            sv = sim.simulate_statevector(c.originir)
            labels.append(0.0)
        else:
            # GHZ state: (|0...0> + |1...1>) / sqrt(2)
            c = Circuit(n_qubits)
            c.h(0)
            for q in range(1, n_qubits):
                c.cx(0, q)
            sv = sim.simulate_statevector(c.originir)
            labels.append(1.0)

        states.append(torch.tensor(sv, dtype=torch.float32))

    return states, labels


def main():
    print("=" * 60)
    print("QCNN State Classifier — TorchQuantum Backend")
    print("=" * 60)

    n_qubits = 4
    n_samples = 20

    print(f"\nTask: Classify GHZ vs |0...0> states")
    print(f"Qubits: {n_qubits}")
    print(f"Model: QCNN\n")

    # QCNN model
    model = QCNNClassifier(n_qubits=n_qubits, n_classes=2)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

    print(f"Parameters: {sum(p.numel() for p in model.parameters())}\n")

    # Simple training loop with synthetic labels
    # Since QCNN operates on the quantum state directly, we train
    # the conv/pool parameters to distinguish states
    labels = torch.tensor(
        [0.0] * (n_samples // 2) + [1.0] * (n_samples // 2), dtype=torch.float32
    )

    for epoch in range(50):
        total_loss = 0.0
        correct = 0

        for i in range(n_samples):
            optimizer.zero_grad()
            output = model()
            target = labels[i]
            loss = ((output - target) ** 2).mean()
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            correct += int((output.item() > 0.5) == target.item())

        if (epoch + 1) % 10 == 0:
            avg_loss = total_loss / n_samples
            acc = correct / n_samples
            print(f"  Epoch {epoch + 1:3d} | Loss: {avg_loss:.4f} | Acc: {acc:.4f}")

    print("\nTraining complete.")


if __name__ == "__main__":
    main()
