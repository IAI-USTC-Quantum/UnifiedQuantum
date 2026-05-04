"""Backward-compatible import path for UnifiedQuantum configuration.

Configuration is now a project-level concern exposed as ``uniqc.config``.
This module remains the implementation and legacy import path during the
compatibility window because older code imports ``uniqc.backend_adapter.config``.

Note: ``CONFIG_FILE`` and the top-level symbols (``CONFIG_DIR``,
``DEFAULT_CONFIG``, ``SUPPORTED_PLATFORMS``, ``META_KEYS``) are imported
from ``uniqc.config`` first so that patching ``uniqc.config.CONFIG_FILE``
propagates here.  All other symbols are then re-exported from ``uniqc.config``.
"""

from uniqc.config import (  # noqa: F401  (local alias so both modules share the same binding)
    CONFIG_DIR,
    CONFIG_FILE,
    DEFAULT_CONFIG,
    META_KEYS,
    PLATFORM_REQUIRED_FIELDS,
    SUPPORTED_PLATFORMS,
)

from uniqc.config import *  # noqa: F401,F403
