"""Download the pinned official RapiDoc distribution and verify its integrity.

To upgrade, obtain version and dist.integrity from the npm rapidoc release,
update VERSION and INTEGRITY below, then run this script and the documentation tests.
Only Python's standard library is required; Node is not needed at build or runtime.
"""

import base64
import hashlib
import io
import tarfile
from pathlib import Path
from urllib.request import urlopen

VERSION = "10.1.0"
INTEGRITY = (
    "sha512-yIlpC2/B3xlxf7Iivea3Db8QtHqFps1bkl7K8VVrEMbBKoh2vu7R8dYmiBI9tiSa"
    "vXP/2japlcSXr4EUYHW1mA=="
)
FILES = {"dist/rapidoc-min.js": "rapidoc-min.js", "LICENSE.txt": "LICENSE.txt"}
DESTINATION = Path(__file__).resolve().parents[1] / "src/hopeit/server/static/rapidoc"


def install(archive: bytes) -> None:
    """Verify the release archive before extracting the selected assets."""
    digest = base64.b64encode(hashlib.sha512(archive).digest()).decode("ascii")
    if f"sha512-{digest}" != INTEGRITY:
        raise ValueError("RapiDoc distribution integrity mismatch")
    assets = {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as package:
        for resource_path, name in FILES.items():
            resource = package.extractfile(f"package/{resource_path}")
            if resource is None:
                raise ValueError(f"Missing RapiDoc asset: {name}")
            assets[name] = resource.read()
    DESTINATION.mkdir(parents=True, exist_ok=True)
    for name, content in assets.items():
        (DESTINATION / name).write_bytes(content)
    (DESTINATION / "VERSION").write_text(VERSION + "\n", encoding="utf-8")


if __name__ == "__main__":
    url = f"https://registry.npmjs.org/rapidoc/-/rapidoc-{VERSION}.tgz"
    with urlopen(url, timeout=60) as response:
        install(response.read())
    print(f"Installed RapiDoc {VERSION} in {DESTINATION}")
