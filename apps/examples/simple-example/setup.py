import setuptools


version = {}
with open("../../../engine/src/hopeit/server/version.py") as fp:
    exec(fp.read(), version)

setuptools.setup(
    name="simple_example",
    version=version['ENGINE_VERSION'],
    description="Hopeit.py Example App",
    package_dir={
        "": "src"
    },
    packages=[
        "common", "model", "simple_example"
    ],
    include_package_data=True,
    python_requires=">=3.7",
    install_requires=[
        "hopeit.engine",
        "hopeit.fs-storage"
    ],
    extras_require={
    },
    entry_points={
    }
)
