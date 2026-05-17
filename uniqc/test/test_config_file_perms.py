"""Tests that ``~/.uniqc/config.yaml`` is written with restrictive perms.

On a multi-user host, writing the config (which can hold provider API
tokens) with the default 0644 umask leaks credentials to every other
local user.  ``save_config`` must use 0600.
"""

from __future__ import annotations

import os
import sys

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="POSIX file-mode bits don't apply on Windows",
)


def test_save_config_writes_0600(tmp_path, monkeypatch) -> None:
    from uniqc import config as uniqc_config

    new_dir = tmp_path / ".uniqc"
    new_file = new_dir / "config.yaml"

    # Redirect both the directory and the file constants so that
    # ``save_config`` (called with no path argument) lands inside tmp_path.
    monkeypatch.setattr(uniqc_config, "CONFIG_DIR", new_dir)
    monkeypatch.setattr(uniqc_config, "CONFIG_FILE", new_file)
    monkeypatch.setenv("HOME", str(tmp_path))

    sample_config = {
        "active_profile": "default",
        "default": {
            "originq": {"token": "super-secret-token-do-not-leak"},
        },
    }

    uniqc_config.save_config(sample_config)

    assert new_file.exists(), "save_config did not create the config file"

    mode = new_file.stat().st_mode & 0o777
    assert mode == 0o600, f"expected 0o600, got {oct(mode)}"

    # The parent directory must not be world- or group-readable either when
    # we created it ourselves.
    parent_mode = new_dir.stat().st_mode & 0o777
    assert parent_mode == 0o700, f"expected parent dir 0o700, got {oct(parent_mode)}"


def test_save_config_retightens_preexisting_file(tmp_path, monkeypatch) -> None:
    from uniqc import config as uniqc_config

    new_dir = tmp_path / ".uniqc"
    new_dir.mkdir(mode=0o700)
    new_file = new_dir / "config.yaml"
    new_file.write_text("placeholder: true\n")
    os.chmod(new_file, 0o644)

    monkeypatch.setattr(uniqc_config, "CONFIG_DIR", new_dir)
    monkeypatch.setattr(uniqc_config, "CONFIG_FILE", new_file)

    uniqc_config.save_config({"active_profile": "default", "default": {}})

    mode = new_file.stat().st_mode & 0o777
    assert mode == 0o600, f"expected 0o600 after rewrite, got {oct(mode)}"
