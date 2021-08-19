import setuptools


version = {}
with open("../../../engine/src/hopeit/server/version.py") as fp:
    exec(fp.read(), version)

setuptools.setup(
    name="hopeit.basic_auth",
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
        f"hopeit.engine=={version['ENGINE_VERSION']}",
        "PyJWT[crypto]>=2.1.0,<3"
    ],
    extras_require={
    },
    entry_points={
    }
)
