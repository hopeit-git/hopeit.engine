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
    version=ENGINE_VERSION,
    install_requires=[f"hopeit.engine=={ENGINE_VERSION}", "redis>=5.0.0"],
)
