import setuptools


setuptools.setup(
    name="simple_example",
    version="0.1.0",
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
        "hopeit.engine"
    ],
    extras_require={
    },
    entry_points={
    }
)
