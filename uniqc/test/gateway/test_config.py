from __future__ import annotations


def test_gateway_default_port_is_18765(tmp_path, monkeypatch):
    monkeypatch.setattr("uniqc.config.CONFIG_FILE", tmp_path / ".uniqc" / "config.yaml")

    from uniqc.gateway.config import DEFAULT_GATEWAY_HOST, DEFAULT_GATEWAY_PORT, load_gateway_config

    cfg = load_gateway_config()

    assert DEFAULT_GATEWAY_HOST == "127.0.0.1"
    assert DEFAULT_GATEWAY_PORT == 18765
    assert cfg == {"host": "127.0.0.1", "port": 18765}


def test_gateway_config_override_preserves_explicit_port(tmp_path, monkeypatch):
    monkeypatch.setattr("uniqc.config.CONFIG_FILE", tmp_path / ".uniqc" / "config.yaml")

    from uniqc import config
    from uniqc.gateway.config import load_gateway_config, save_gateway_config

    save_gateway_config(port=19000, host="0.0.0.0")

    assert load_gateway_config() == {"host": "0.0.0.0", "port": 19000}
    assert config.load_config()["gateway"] == {"host": "0.0.0.0", "port": 19000}
