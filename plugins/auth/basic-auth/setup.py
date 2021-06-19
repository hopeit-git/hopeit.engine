import setuptools


version = {}
with open("../../../engine/src/hopeit/server/version.py") as fp:
    exec(fp.read(), version)

setuptools.setup(
    name="hopeit.plugins.basic_auth",
    version=version['ENGINE_VERSION'],
    description="Hopeit.py Basic Auth Plugin",
    package_dir={
        "": "src"
    },
    packages=[
        "hopeit.basic_auth"
    ],
    include_package_data=True,
    package_data={
        "hopeit.basic_auth": ["py.typed"]
    },
    python_requires=">=3.7",
    install_requires=[
        "hopeit.engine",
        "pyjwt[crypto]>=1.7.0,<2"
    ],
    extras_require={
    },
    entry_points={
    }
)
