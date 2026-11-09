"""Build the Gateway once for developers; ship verified assets in source releases.

Published source archives contain both the frontend sources and their built
assets. Building those archives requires Python only. A changed source checkout
rebuilds with the committed npm lock instead of silently shipping stale assets.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from setuptools import build_meta as _backend

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"
STATIC = ROOT / "uniqc/gateway/static"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sources() -> dict[str, str]:
    paths = [FRONTEND / name for name in
             ("package.json", "package-lock.json", "index.html", "vite.config.ts", "tsconfig.json")]
    paths.extend(p for p in (FRONTEND / "src").rglob("*") if p.is_file())
    paths.extend(p for p in FRONTEND.glob("tsconfig.*.json") if p.is_file())
    paths.extend(p for p in (FRONTEND / "public").rglob("*") if p.is_file())
    return {p.relative_to(FRONTEND).as_posix(): _digest(p) for p in sorted(set(paths))}


def _assets() -> dict[str, str]:
    return {p.relative_to(STATIC).as_posix(): _digest(p) for p in sorted(STATIC.rglob("*"))
            if p.is_file() and p.name != "build-manifest.json"}


def _copy_notices() -> None:
    """Retain production notices and the build tools that emit runtime code."""
    lock = json.loads((FRONTEND / "package-lock.json").read_text(encoding="utf-8"))
    records = []
    emitted_runtime = {"node_modules/tailwindcss", "node_modules/vite",
                       "node_modules/esbuild", "node_modules/rollup"}
    for relative, entry in sorted(lock["packages"].items()):
        if not relative or (entry.get("dev") and relative not in emitted_runtime):
            continue
        package = FRONTEND / relative
        notices = [p for p in package.iterdir() if p.is_file()
                   and p.name.lower().startswith(("license", "licence", "copying", "notice"))]
        if not notices:
            raise RuntimeError(f"Frontend dependency has no original notice: {relative}")
        target = STATIC / "third-party" / relative.removeprefix("node_modules/")
        target.mkdir(parents=True, exist_ok=True)
        for path in notices:
            shutil.copyfile(path, target / path.name)
        records.append({"package": relative, "version": entry["version"],
                        "scope": "emitted runtime build tool" if entry.get("dev") else "production dependency",
                        "notices": {p.name: _digest(p) for p in sorted(notices)}})
    (STATIC / "third-party/dependencies.json").write_text(
        json.dumps(records, indent=2) + "\n", encoding="utf-8")


def ensure_frontend() -> None:
    """Reuse only a complete, source-matched frontend; otherwise build from lock."""
    sources = _sources()
    manifest = STATIC / "build-manifest.json"
    if manifest.is_file():
        recorded = json.loads(manifest.read_text(encoding="utf-8"))
        if (recorded.get("builder_sha256") == _digest(Path(__file__))
                and recorded.get("sources") == sources and recorded.get("assets") == _assets()
                and "index.html" in recorded.get("assets", {})):
            return
    npm = shutil.which("npm")
    if npm is None:
        raise RuntimeError("Building changed Gateway sources requires npm. Published source archives include verified assets.")
    subprocess.run([npm, "ci", "--no-audit", "--no-fund"], cwd=FRONTEND, check=True)
    subprocess.run([npm, "run", "build"], cwd=FRONTEND, check=True)
    built = FRONTEND / "dist"
    if not (built / "index.html").is_file():
        raise RuntimeError("Gateway build did not produce index.html")
    # Remove stale hashed chunks rather than mixing frontend versions.
    if STATIC.exists():
        shutil.rmtree(STATIC)
    shutil.copytree(built, STATIC)
    _copy_notices()
    manifest.write_text(json.dumps({"schema": "uniqc.gateway-assets.v1",
                                    "builder_sha256": _digest(Path(__file__)), "sources": sources,
                                    "assets": _assets()}, indent=2) + "\n", encoding="utf-8")


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    ensure_frontend()
    return _backend.build_wheel(wheel_directory, config_settings, metadata_directory)


def build_sdist(sdist_directory, config_settings=None):
    ensure_frontend()
    return _backend.build_sdist(sdist_directory, config_settings)


def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
    ensure_frontend()
    return _backend.build_editable(wheel_directory, config_settings, metadata_directory)


get_requires_for_build_wheel = _backend.get_requires_for_build_wheel
get_requires_for_build_sdist = _backend.get_requires_for_build_sdist
get_requires_for_build_editable = _backend.get_requires_for_build_editable
prepare_metadata_for_build_wheel = _backend.prepare_metadata_for_build_wheel
prepare_metadata_for_build_editable = _backend.prepare_metadata_for_build_editable
