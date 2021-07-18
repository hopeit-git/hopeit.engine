import setuptools

version = {}
with open("../../../engine/src/hopeit/server/version.py") as fp:
    exec(fp.read(), version)

setuptools.setup(
    name="hopeit.plugins.samsa",
    version=version['ENGINE_VERSION'],
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
        f"hopeit.engine=={version['ENGINE_VERSION']}",
    ],
    extras_require={
    },
    entry_points={
    }
)
