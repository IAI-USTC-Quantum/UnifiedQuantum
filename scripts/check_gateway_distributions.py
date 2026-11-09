"""Test the actual wheel and actual source archive outside the source checkout.

Usage: python scripts/check_gateway_distributions.py dist
Requires uv. The source-archive build deliberately has no Node/npm in PATH and
uses offline Python build dependencies, proving that end users need only Python.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist", type=Path)
    args = parser.parse_args()
    directory = args.dist.resolve(strict=True)
    wheels, sources = list(directory.glob("*.whl")), list(directory.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sources) != 1:
        raise ValueError("Expected exactly one wheel and one source archive")
    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError("uv is required for isolated artifact validation")
    checker = Path(__file__).with_name("check_installed_gateway.py").resolve()
    env = os.environ.copy()
    for name in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"):
        env.pop(name, None)
    # Isolate user configuration without discarding the build dependencies
    # cached by the preceding real source build. Only the archive build is offline.
    if "UV_CACHE_DIR" not in env:
        env["UV_CACHE_DIR"] = subprocess.check_output([uv, "cache", "dir"], env=env, text=True).strip()
    with tempfile.TemporaryDirectory(prefix="uniqc-product-") as temporary:
        work = Path(temporary)
        env["HOME"] = str(work / "home")
        env["USERPROFILE"] = str(work / "home")
        env["OMP_NUM_THREADS"] = "1"
        env["OPENBLAS_NUM_THREADS"] = "1"
        target = work / "env"
        subprocess.run([uv, "venv", str(target), "--python", sys.executable], env=env, check=True)
        python = target / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run([uv, "pip", "install", "--python", str(python), str(wheels[0]), "httpx"],
                       env=env, check=True)
        subprocess.run([str(python), str(checker)], cwd=work, env=env, check=True)
        source = work / "source"
        with tarfile.open(sources[0]) as archive:
            for member in archive.getmembers():
                path = Path(member.name)
                if (path.is_absolute() or ".." in path.parts or member.issym() or member.islnk()
                        or "node_modules" in path.parts or ".git" in path.parts):
                    raise ValueError("Unsafe or non-self-contained source archive: " + member.name)
            archive.extractall(source, filter="data")
        roots = list(source.iterdir())
        if len(roots) != 1:
            raise ValueError("Expected one source archive root")
        no_node = {**env, "PATH": str(work / "no-node-tools"), "UV_PYTHON": sys.executable}
        built = work / "sdist-wheel"
        subprocess.run([uv, "build", "--offline", "--wheel", str(roots[0]), "--out-dir", str(built)],
                       env=no_node, cwd=work, check=True)
        actual = list(built.glob("*.whl"))
        if len(actual) != 1:
            raise ValueError("Source archive did not produce exactly one wheel")
        subprocess.run([uv, "pip", "install", "--python", str(python), "--reinstall", "--no-deps", str(actual[0])],
                       env=env, check=True)
        subprocess.run([str(python), str(checker)], cwd=work, env=env, check=True)
    print("PASS actual wheel and Node-free source archive: installed native CLI, API and SPA")


if __name__ == "__main__":
    main()
