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


def test_audit_backends_reports_fetch_failures():
    """audit_backends with fetch_failures emits platform-level warning issues."""
    backend = BackendInfo(
        platform=Platform.ORIGINQ,
        name="test-chip",
        num_qubits=5,
        topology=(QubitTopology(0, 1),),
        status="available",
        is_simulator=False,
        is_hardware=True,
    )
    failures = {Platform.QUARK: "connection timeout"}
    issues = audit_backends([backend], fetch_failures=failures)

    # Should have the platform fetch issue plus the valid backend (no issues)
    platform_issues = [i for i in issues if i.field == "platform_fetch"]
    assert len(platform_issues) == 1
    assert platform_issues[0].severity == "warning"
    assert "quark" in platform_issues[0].message
    assert platform_issues[0].backend_id == "quark:__platform__"


def test_fetch_platform_backends_skips_without_credentials(tmp_path, monkeypatch):
    """Platforms without credentials should be skipped silently."""
    from uniqc.backend_adapter.backend_registry import fetch_platform_backends

    # Point to empty config so has_platform_credentials returns False
    monkeypatch.setattr("uniqc.config.CONFIG_FILE", tmp_path / "config.yaml")
    backends, fresh = fetch_platform_backends(Platform.ORIGINQ)
    assert backends == []
    assert fresh is False


def test_has_platform_credentials(tmp_path, monkeypatch):
    """has_platform_credentials returns False when no token is configured."""
    from uniqc.config import has_platform_credentials

    # Point to a temp empty config
    monkeypatch.setattr("uniqc.config.CONFIG_FILE", tmp_path / "config.yaml")
    assert has_platform_credentials("originq") is False
    assert has_platform_credentials("quafu") is False
    assert has_platform_credentials("quark") is False
    assert has_platform_credentials("ibm") is False
