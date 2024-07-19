import setuptools


version = {}
with open("../../../engine/src/hopeit/server/version.py") as fp:
    exec(fp.read(), version)

setuptools.setup(
    name="client_example",
    version=version['ENGINE_VERSION'],
    description="Hopeit.py Client Example App",
    package_dir={
        "": "src"
    },
    packages=[
        "client_example"
    ],
    include_package_data=True,
    python_requires=">=3.9",
    install_requires=[
        f"hopeit.engine[web,cli,apps-client]=={version['ENGINE_VERSION']}",
        f"hopeit.basic-auth=={version['ENGINE_VERSION']}",
        f"simple-example=={version['ENGINE_VERSION']}"
    ],
    extras_require={
    },
    entry_points={
    }
)
