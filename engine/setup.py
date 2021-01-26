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
    version="0.1.2",
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
<<<<<<< HEAD
        "PyJWT[crypto]",
        "click",
        "deepdiff",
        "typing-inspect"
    ]],
=======
        "cryptography",
        "pyjwt",
        "click",
        "deepdiff",
        "typing_inspect"
    ],
>>>>>>> add summary to method api
    extras_require={
        "web": [ f"{lib}=={libversion(lib)}" for lib in [
            "aiohttp",
            "aiohttp-cors",
            "aiohttp-swagger3",
            "dataclasses-jsonschema[fast-validation]",
<<<<<<< HEAD
            "fastjsonschema"
<<<<<<< HEAD
        ]],
        "cli": [ f"{lib}=={libversion(lib)}" for lib in [
            "dataclasses-jsonschema[fast-validation]",
            "fastjsonschema"
        ]]
=======
=======
            "fastjsonschema==2.14.3"
>>>>>>> cleanup; typo
        ],
        "cli": [
            "dataclasses-jsonschema[fast-validation]",
            "fastjsonschema==2.14.3"
        ]
>>>>>>> add summary to method api
    },
    entry_points={
        "console_scripts": [
            "hopeit_server = hopeit.cli.server:server",
            "hopeit_openapi = hopeit.cli.openapi:openapi"
        ]
    }
)
