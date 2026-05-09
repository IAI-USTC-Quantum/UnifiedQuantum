"""00 — 配置 Key 与后端缓存

[doc-require: ]
[doc-output-include: stdout, source]

最早的用户路径：创建配置、写入平台 token（脱敏）、校验配置结构，并用本地构造的
``BackendInfo`` 演示后端缓存的写入、读取和审查。真实 token 不会写入文档输出。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from uniqc import BackendInfo, Platform, QubitTopology, audit_backends
from uniqc.backend_adapter.backend_cache import (
    cache_info,
    get_cached_backends,
    update_cache,
)
from uniqc.backend_adapter.config import load_config, save_config, validate_config


def main() -> None:
    workdir = Path(tempfile.mkdtemp(prefix="uniqc-bp-config-"))
    config_path = workdir / "config.yaml"

    config = {
        "active_profile": "release-check",
        "release-check": {
            "originq": {"token": "originq-token-redacted"},
            "quafu": {"token": "quafu-token-redacted"},
            "ibm": {"token": "ibm-token-redacted", "proxy": {"http": "", "https": ""}},
        },
    }
    save_config(config, config_path=config_path)

    loaded = load_config(config_path=config_path)
    errors = validate_config(config_path=config_path)
    print("profile:", loaded["active_profile"])
    print("validation errors:", errors)

    backend = BackendInfo(
        platform=Platform.DUMMY,
        name="virtual-line-3",
        description="release-check virtual backend",
        num_qubits=3,
        topology=(QubitTopology(0, 1), QubitTopology(1, 2)),
        status="available",
        is_simulator=True,
    )
    update_cache(Platform.DUMMY, [backend], cache_dir=workdir)
    cached = get_cached_backends(Platform.DUMMY, cache_dir=workdir)
    print("cached backend ids:", [b.full_id() for b in cached])
    print("cache platforms:", sorted(cache_info(cache_dir=workdir)))
    print("audit issues:", audit_backends(cached))


if __name__ == "__main__":
    main()
