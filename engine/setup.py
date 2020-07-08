import setuptools

setuptools.setup(
    name="hopeit.engine",
    version="0.1.0",
    description="Hopeit.py Engine",
    package_dir={
        "": "src"
    },
    packages=[
        "hopeit.app",
        "hopeit.cli",
        "hopeit.dataobjects",
        "hopeit.server",
        "hopeit.testing",
        "hopeit.toolkit",
        "hopeit.toolkit.storage"
    ],
    include_package_data=True,
    python_requires=">=3.7",
    install_requires=[
        "aiojobs",
        "aiofiles",
        "aioredis",
        "lz4",
        "stringcase",
        "cryptography",
        "pyjwt",
        "click",
        "deepdiff",
        "typing_inspect"
    ],
    extras_require={
        "web": [
            "aiohttp",
            "aiohttp_cors",
            "aiohttp-swagger3",
            "dataclasses-jsonschema[fast-validation]",
            "fastjsonschema==2.14.3"
        ],
        "cli": [
            "dataclasses-jsonschema[fast-validation]",
            "fastjsonschema==2.14.3"
        ]
    },
    entry_points={
        "console_scripts": [
            "hopeit_server = hopeit.cli.server:server",
            "hopeit_openapi = hopeit.cli.openapi:openapi"
        ]
    }
)
