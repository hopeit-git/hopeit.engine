"""Download the pinned official Swagger UI distribution and verify its integrity.

To upgrade, obtain version and dist.integrity from the npm swagger-ui-dist release,
update VERSION and INTEGRITY below, then run this script and the documentation tests.
Only Python's standard library is required; Node is not needed at build or runtime.
"""

import base64
import hashlib
import io
import tarfile
from pathlib import Path
from urllib.request import urlopen

VERSION = "5.33.0"
INTEGRITY = (
    "sha512-wpdK+m6BU5yj6pmUdMskZVTSWYG4DLglAx3sIhylloY37i8O37IrH+YEpqdXNfpa"
    "TGxILRBFzUqLF2jKqbfI7A=="
)
FILES = (
    "swagger-ui-bundle.js",
    "swagger-ui-bundle.js.LICENSE.txt",
    "swagger-ui.css",
    "favicon-32x32.png",
    "LICENSE",
    "NOTICE",
)
DESTINATION = Path(__file__).resolve().parents[1] / "src/hopeit/server/static/swagger_ui"


def install(archive: bytes) -> None:
    """Verify the release archive before extracting the selected assets."""
    digest = base64.b64encode(hashlib.sha512(archive).digest()).decode("ascii")
    if f"sha512-{digest}" != INTEGRITY:
        raise ValueError("Swagger UI distribution integrity mismatch")
    assets = {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as package:
        for name in FILES:
            resource = package.extractfile(f"package/{name}")
            if resource is None:
                raise ValueError(f"Missing Swagger UI asset: {name}")
            assets[name] = resource.read()
    DESTINATION.mkdir(parents=True, exist_ok=True)
    for name, content in assets.items():
        (DESTINATION / name).write_bytes(content)
    (DESTINATION / "VERSION").write_text(VERSION + "\n", encoding="utf-8")


if __name__ == "__main__":
    url = f"https://registry.npmjs.org/swagger-ui-dist/-/swagger-ui-dist-{VERSION}.tgz"
    with urlopen(url, timeout=60) as response:
        install(response.read())
    print(f"Installed Swagger UI {VERSION} in {DESTINATION}")
