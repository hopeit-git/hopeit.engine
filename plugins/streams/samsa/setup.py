import setuptools


setuptools.setup(
    name="hopeit.plugins.samsa",
    version="0.2.0",
    description="Hopeit.py Streams Samsa Plugin",
    package_dir={
        "": "src"
    },
    packages=[
        "hopeit.samsa"
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
