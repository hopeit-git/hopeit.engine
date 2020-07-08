import setuptools


setuptools.setup(
    name="hopeit.plugins.basic_auth",
    version="0.1.0",
    description="Hopeit.py Basic Auth Plugin",
    package_dir={
        "": "src"
    },
    packages=[
        "hopeit.basic_auth"
    ],
    include_package_data=True,
    python_requires=">=3.7",
    install_requires=[
        "hopeit.engine",
        "cryptography",
        "pyjwt"
    ],
    extras_require={
    },
    entry_points={
    }
)
