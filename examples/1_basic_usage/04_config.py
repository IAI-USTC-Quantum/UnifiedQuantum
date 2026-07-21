"""04 — Configuration: ``uniqc config`` + ``~/.uniqc/config.yaml``

[doc-require: ]
[doc-output-include: stdout, source]

只演示**只读**的配置 API：本例不会去碰真实的 ``~/.uniqc/config.yaml``，而是写到一个
临时文件再读回来。

实际使用时推荐三种方式之一：

1. ``uniqc config init`` + ``uniqc config set originq.token <YOUR_TOKEN>``
2. 手动编辑 ``~/.uniqc/config.yaml``
3. 用 ``UNIQC_PROFILE`` 环境变量切换 profile
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from uniqc.backend_adapter.config import load_config, save_config, validate_config


def main() -> None:
    workdir = Path(tempfile.mkdtemp(prefix="uniqc-config-demo-"))
    config_path = workdir / "config.yaml"

    save_config(
        {
            "active_profile": "demo",
            "demo": {
                "originq": {"token": "originq-token-redacted"},
                "quark": {"QUARK_API_KEY": "quark-token-redacted"},
                "ibm": {
                    "token": "ibm-token-redacted",
                    "proxy": {"http": "", "https": ""},
                },
            },
        },
        config_path=config_path,
    )

    loaded = load_config(config_path=config_path)
    errors = validate_config(config_path=config_path)

    print("written to: <temporary-directory>/config.yaml")
    print("active profile:", loaded["active_profile"])
    print("originq token (redacted):", loaded["demo"]["originq"]["token"])
    print("validation errors:", errors)
    print()
    print("CLI equivalents:")
    print("  uniqc config init")
    print("  uniqc config set originq.token YOUR_TOKEN")
    print("  uniqc config set ibm.proxy.http http://proxy.example.com:8080")
    print("  uniqc config validate")


if __name__ == "__main__":
    main()
