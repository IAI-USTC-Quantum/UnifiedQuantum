"""Audit a real installed wheel, its bundled SPA, CLI and native local demo.

Run in a clean wheel environment with httpx installed. Run from outside the
source checkout so neither the package nor the UI can resolve to source files.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from importlib.metadata import distribution
from pathlib import Path


def main() -> None:
    from fastapi.testclient import TestClient

    import uniqc
    from uniqc.gateway.server import create_app

    dist = distribution("unified-quantum")
    installed = Path(uniqc.__file__).resolve()
    if not installed.is_relative_to(Path(dist.locate_file("")).resolve()):
        raise ValueError("Gateway check resolved to a source checkout")
    static = installed.parent / "gateway/static"
    manifest = json.loads((static / "build-manifest.json").read_text(encoding="utf-8"))
    for name, digest in manifest["assets"].items():
        path = static / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("Changed or omitted packaged frontend asset: " + name)
    if not (static / "third-party/dependencies.json").is_file():
        raise ValueError("Missing original frontend dependency notices")
    with TestClient(create_app()) as client:
        assert client.get("/api/health").json() == {"status": "ok"}
        assert client.get("/api/version").json()["version"] == dist.version
        for route in ("/", "/demo", "/backends", "/tasks", "/archive"):
            response = client.get(route)
            assert response.status_code == 200 and response.content == (static / "index.html").read_bytes()
        for name in manifest["assets"]:
            response = client.get("/" + name)
            assert response.status_code == 200 and response.content == (static / name).read_bytes()
        assert client.get("/assets/omitted.js").status_code == 404
        for case in ("ghz", "w", "ramsey"):
            response = client.post("/api/demo/simulate", json={"case": case, "qubits": 4, "phase": 0.73})
            assert response.status_code == 200, response.text
            data = response.json()
            assert data["max_probability_error"] < 1e-10
            assert abs(data["probability_sum"] - 1) < 1e-10
    cli = subprocess.run([sys.executable, "-m", "uniqc.cli", "demo", "--case", "ghz", "--qubits", "3"],
                         check=True, capture_output=True, text=True)
    assert json.loads(cli.stdout)["max_probability_error"] < 1e-10
    print(json.dumps({"version": dist.version, "package": str(installed),
                      "verified_assets": len(manifest["assets"]), "real_native_presets": 3,
                      "spa_routes": 5, "cli": "passed"}))


if __name__ == "__main__":
    main()
