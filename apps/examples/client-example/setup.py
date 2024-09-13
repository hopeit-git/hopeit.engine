from setuptools import setup
from os import environ

version = {}
try:
    with open("../../../engine/src/hopeit/server/version.py") as fp:
        exec(fp.read(), version)
        ENGINE_VERSION = version["ENGINE_VERSION"]
except FileNotFoundError:
    ENGINE_VERSION = environ.get("ENGINE_VERSION")

if not ENGINE_VERSION:
    raise RuntimeError("ENGINE_VERSION is not specified.")

setup(
    version=version["ENGINE_VERSION"],
    install_requires=[
        f"hopeit.engine[web,cli,apps-client]=={version['ENGINE_VERSION']}",
        f"hopeit.basic-auth=={version['ENGINE_VERSION']}",
        f"simple-example=={version['ENGINE_VERSION']}",
    ],
)
