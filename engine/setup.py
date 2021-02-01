import setuptools

def read_requirements_lock():
    with open("requirements.lock") as fb:
        libs = {}
        for line in fb.readlines():
            lv = line.split("==")
            if len(lv) >  1:
                libs[lv[0]] = lv[1].strip('\n')
    return libs

versions = read_requirements_lock()


def libversion(lib):
    return versions[lib.split('[')[0]]


setuptools.setup(
    name="hopeit.engine",
    version="0.1.3",
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
    install_requires=[ f"{lib}=={libversion(lib)}" for lib in [
        "aiojobs",
        "aiofiles",
        "aioredis",
        "lz4",
        "stringcase",
        "PyJWT[crypto]",
        "click",
        "deepdiff",
        "typing-inspect"
    ]],
    extras_require={
        "web": [ f"{lib}=={libversion(lib)}" for lib in [
            "aiohttp",
            "aiohttp-cors",
            "aiohttp-swagger3",
            "dataclasses-jsonschema[fast-validation]",
            "fastjsonschema"
        ]],
        "cli": [ f"{lib}=={libversion(lib)}" for lib in [
            "dataclasses-jsonschema[fast-validation]",
            "fastjsonschema"
        ]]
    },
    entry_points={
        "console_scripts": [
            "hopeit_server = hopeit.cli.server:server",
            "hopeit_openapi = hopeit.cli.openapi:openapi"
        ]
    }
)
