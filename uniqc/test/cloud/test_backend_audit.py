from uniqc.backend_adapter.backend_info import BackendInfo, Platform, QubitTopology
from uniqc.backend_adapter.backend_registry import audit_backend_info, audit_backends


def test_backend_audit_accepts_valid_backend():
    backend = BackendInfo(
        platform=Platform.DUMMY,
        name="dummy-line",
        num_qubits=2,
        topology=(QubitTopology(0, 1),),
        status="available",
        is_simulator=False,
        is_hardware=True,
        avg_1q_fidelity=0.99,
    )

    assert audit_backend_info(backend) == []


def test_backend_audit_reports_invalid_topology_and_fidelity():
    backend = BackendInfo(
        platform=Platform.DUMMY,
        name="bad",
        num_qubits=1,
        topology=(QubitTopology(0, 2),),
        status="online-ish",
        is_simulator=True,
        is_hardware=True,
        avg_1q_fidelity=1.2,
    )

    issues = audit_backends([backend])
    fields = {issue.field for issue in issues}
    severities = {issue.severity for issue in issues}

    assert {"kind", "status", "avg_1q_fidelity", "topology"} <= fields
    assert "error" in severities
