from setuptools import setup

version = {}
with open("../../../engine/src/hopeit/server/version.py") as fp:
    exec(fp.read(), version)

setup(
    version=version["ENGINE_VERSION"],
    install_requires=[
        f"hopeit.engine[web,cli,apps-client]=={version['ENGINE_VERSION']}",
        f"hopeit.basic-auth=={version['ENGINE_VERSION']}",
        f"simple-example=={version['ENGINE_VERSION']}",
    ],
)
