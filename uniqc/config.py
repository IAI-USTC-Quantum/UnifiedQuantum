"""Top-level UnifiedQuantum configuration API.

Configuration is project-wide state, not backend-adapter-only state.  The
implementation remains shared with ``uniqc.backend_adapter.config`` for
backward compatibility, so both import paths refer to the same module object.
"""

from __future__ import annotations

import sys

from uniqc.backend_adapter import config as _config

sys.modules[__name__] = _config
