from setuptools import setup

version = {}
with open("../../../engine/src/hopeit/server/version.py") as fp:
    exec(fp.read(), version)

setup(
    version=version["ENGINE_VERSION"],
    install_requires=[
        f"hopeit.engine[fs-storage]=={version['ENGINE_VERSION']}",
        "pandas",
        "numpy",
    ],
    extras_require={
        "pyarrow": ["pyarrow"],
    },
)
