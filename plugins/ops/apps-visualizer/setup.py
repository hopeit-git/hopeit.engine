from setuptools import setup

version = {}
with open("../../../engine/src/hopeit/server/version.py") as fp:
    exec(fp.read(), version)

setup(
    version=version["ENGINE_VERSION"],
    install_requires=[
        f"hopeit.engine[web,log-streamer,config-manager]=={version['ENGINE_VERSION']}"
    ],
)
