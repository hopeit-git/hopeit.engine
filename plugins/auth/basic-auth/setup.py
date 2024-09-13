from setuptools import setup

version = {}
with open("../../../engine/src/hopeit/server/version.py") as fp:
    exec(fp.read(), version)

setup(
    version=version["ENGINE_VERSION"],
    install_requires=[
        f"hopeit.engine=={version['ENGINE_VERSION']}",
        "PyJWT[crypto]>=2.8.0",
    ],
)
