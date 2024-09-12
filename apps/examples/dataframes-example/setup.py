import setuptools

version = {}
with open("../../../engine/src/hopeit/server/version.py") as fp:
    exec(fp.read(), version)

setuptools.setup(
    name="dataframes_example",
    version=version["ENGINE_VERSION"],
    description="hopeit.engine dataframes example app",
    package_dir={"": "src"},
    packages=[
        "dataframes_example",
    ],
    include_package_data=True,
    python_requires=">=3.9",
    install_requires=[
        f"hopeit.engine[web,cli,redis-streams]=={version['ENGINE_VERSION']}",
        f"hopeit.dataframes[pyarrow]=={version['ENGINE_VERSION']}",
        f"scikit-learn",
    ],
)
