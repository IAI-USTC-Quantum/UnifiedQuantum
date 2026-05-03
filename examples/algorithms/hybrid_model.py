"""Hybrid Classical-Quantum Model using TorchQuantum backend.

Demonstrates a hybrid architecture: Classical encoder → Quantum circuit
→ Classical decoder, for 2D binary classification.
"""

try:
    import torch
    import torch.nn as nn
    from sklearn.datasets import make_moons
    from sklearn.preprocessing import StandardScaler

    from uniqc import HybridQCLModel
except ImportError as e:
    print(f"Required dependencies not available: {e}")
    print("Install with: pip install unified-quantum[pytorch] scikit-learn")
    print('Then install TorchQuantum manually: pip install "torchquantum @ git+https://github.com/Agony5757/torchquantum.git@fix/optional-qiskit-deps"')
    raise SystemExit(1)


def main():
    print("=" * 60)
    print("Hybrid Classical-Quantum Model — TorchQuantum Backend")
    print("=" * 60)

    # Generate dataset
    X_np, y_np = make_moons(n_samples=100, noise=0.15, random_state=42)
    scaler = StandardScaler()
    X_np = scaler.fit_transform(X_np)
    X = torch.tensor(X_np, dtype=torch.float32)
    y = torch.tensor(y_np, dtype=torch.float32).unsqueeze(1)

    # Model
    model = HybridQCLModel(
        n_features=2,
        n_qubits=4,
        quantum_depth=2,
        classical_hidden=16,
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    loss_fn = nn.BCELoss()

    n_params = sum(p.numel() for p in model.parameters())
    print(f"\nDataset: make_moons (100 samples)")
    print(f"Model: HybridQCLModel (classical → quantum → classical)")
    print(f"Total parameters: {n_params}")
    print(f"  Encoder:  {sum(p.numel() for p in model.encoder.parameters())}")
    print(f"  Quantum:  {model.quantum_params.numel()}")
    print(f"  Decoder:  {sum(p.numel() for p in model.decoder.parameters())}\n")

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
