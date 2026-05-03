"""Generate Python stubs for the C++ simulator extension."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    try:
        import pybind11_stubgen  # noqa: F401
    except ImportError:
        print("pybind11-stubgen is not installed; install it before generating C++ stubs.")
        return 1

    return subprocess.run(
        ["pybind11-stubgen", "uniqc_cpp", "-o", str(PROJECT_ROOT / "uniqc" / "simulator")],
        cwd=PROJECT_ROOT,
        check=False,
    ).returncode


if __name__ == "__main__":
    sys.exit(main())
