import setuptools

version = {}
with open("../../../engine/src/hopeit/server/version.py") as fp:
    exec(fp.read(), version)

setuptools.setup(
    version=version["ENGINE_VERSION"],
    install_requires=[
        f"hopeit.engine[web,cli,redis-streams]=={version['ENGINE_VERSION']}",
        f"hopeit.dataframes[pyarrow]=={version['ENGINE_VERSION']}",
        f"scikit-learn",
    ],
)
