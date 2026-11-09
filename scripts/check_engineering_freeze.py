"""Verify the business sources preserved by the standalone-product change."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "engineering-business-freeze.json").read_text(encoding="utf-8"))
    for record in manifest["files"]:
        data = (root / record["path"]).read_bytes().replace(b"\r\n", b"\n")
        if hashlib.sha256(data).hexdigest() != record["sha256"]:
            raise ValueError("Frozen implementation changed: " + record["path"])
    print(f"Preserved {len(manifest['files'])} business source files from {manifest['source_commit']}")


if __name__ == "__main__":
    main()
