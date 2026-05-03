"""QNN Binary Classifier using TorchQuantum backend.

Demonstrates a Quantum Neural Network for binary classification on
a synthetic moons dataset with native PyTorch autograd.
"""

try:
    import torch
    import torch.nn as nn
    from sklearn.datasets import make_moons
    from sklearn.preprocessing import StandardScaler

    from uniqc import QNNClassifier
except ImportError as e:
    print(f"Required dependencies not available: {e}")
    print("Install with: pip install unified-quantum[pytorch] scikit-learn")
    print('Then install TorchQuantum manually: pip install "torchquantum @ git+https://github.com/Agony5757/torchquantum.git@fix/optional-qiskit-deps"')
    raise SystemExit(1)


def main():
    print("=" * 60)
    print("QNN Binary Classifier — TorchQuantum Backend")
    print("=" * 60)

    # Generate moons dataset
    X_np, y_np = make_moons(n_samples=100, noise=0.15, random_state=42)
    scaler = StandardScaler()
    X_np = scaler.fit_transform(X_np)
    X = torch.tensor(X_np, dtype=torch.float32)
    y = torch.tensor(y_np, dtype=torch.float32)

    # Model
    n_qubits = 4
    model = QNNClassifier(n_qubits=n_qubits, n_features=2, depth=2)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    loss_fn = nn.BCELoss()

    print(f"\nDataset: make_moons (100 samples, 2 features)")
    print(f"Model: QNN (n_qubits={n_qubits}, depth=2)")
    print(f"Parameters: {sum(p.numel() for p in model.parameters())}\n")

    # Training
    for epoch in range(50):
        optimizer.zero_grad()
        y_pred = model(X)
        loss = loss_fn(y_pred, y)
        loss.backward()
        optimizer.step()

        if (epoch + 1) % 10 == 0:
            acc = ((y_pred > 0.5).float() == y).float().mean()
            print(f"  Epoch {epoch + 1:3d} | Loss: {loss.item():.4f} | Acc: {acc:.4f}")

    # Final accuracy
    with torch.no_grad():
        y_pred = model(X)
        acc = ((y_pred > 0.5).float() == y).float().mean()
    print(f"\nFinal accuracy: {acc:.4f}")


if __name__ == "__main__":
    main()
