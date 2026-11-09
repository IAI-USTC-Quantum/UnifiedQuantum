"""Tests for the experiment coverage manifest and its CLI surface."""

from __future__ import annotations

import json

from uniqc.experiments import get_manifest, render_text


def test_manifest_entries_are_complete():
    manifest = get_manifest()
    assert len(manifest) >= 9
    required_ids = {
        "xeb",
        "readout_calibration",
        "readout_em",
        "zne",
        "state_tomography",
        "classical_shadow",
        "noise_model_exchange",
        "quantum_volume",
        "compile_execute_throughput",
    }
    assert required_ids <= {entry["id"] for entry in manifest}
    for entry in manifest:
        assert entry["category"] in {"calibration", "mitigation", "tomography", "benchmark"}
        assert entry["unified_interface"], entry["id"]
        assert entry["status"], entry["id"]
        assert entry["record_sources"], entry["id"]


def test_manifest_is_a_copy():
    manifest = get_manifest()
    manifest[0]["id"] = "mutated"
    assert get_manifest()[0]["id"] != "mutated"


def test_zne_placeholder_registered_separately():
    entry = next(e for e in get_manifest() if e["id"] == "zne")
    assert entry["status"] == "unimplemented_placeholder__registered"
    assert entry["local_verify"] is None
    assert "placeholder" in entry["retest_note"]


def test_manifest_json_serializable():
    json.dumps(get_manifest(), ensure_ascii=False)


def test_render_text_mentions_every_entry():
    text = render_text()
    for entry in get_manifest():
        assert entry["id"] in text
    assert "engineering-business-freeze.json" in text


def test_frozen_business_entries_carry_retest_commands():
    for entry in get_manifest():
        if entry["status"] == "frozen_business__local_verify_available":
            assert entry["retest_command"], entry["id"]
            assert entry["local_verify"], entry["id"]
            assert "do not run this round" in entry["retest_note"].lower()
