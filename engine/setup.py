import setuptools

version = {}
with open("src/hopeit/server/version.py") as fp:
    exec(fp.read(), version)


def read_requirements_txt():
    with open("requirements.txt") as fb:
        libs = {}
        for line in fb.readlines():
            for op in (">=", "=="):
                try:
                    idx = line.index(op)
                    libs[line[0:idx]] = line[idx+2:]
                except ValueError:
                    pass
    return libs

def read_requirements_lock():
    with open("requirements.lock") as fb:
        libs = {}
        for line in fb.readlines():
            lv = line.split("==")
            if len(lv) >  1:
                libs[lv[0]] = lv[1].strip('\n')
    return libs

req_versions = read_requirements_txt()
locked_versions = read_requirements_lock()


def libversion(lib):
    lib_source = "requirements.txt"
    lib_version = req_versions.get(lib)
    if lib_version is None:
        lib_source = "requirements.lock"
        lib_version = locked_versions[lib.split('[')[0]]
    print(lib_source, f"{lib}>={lib_version}")
    return lib_version


setuptools.setup(
    name="hopeit.engine",
    version=version['ENGINE_VERSION'],
    description="Hopeit Engine: Microservices with Streams",
    license="Apache 2",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    author="Leo Smerling and Pablo Canto",
    author_email="contact@hopeit.com.ar",
    url="https://github.com/hopeit-git/hopeit.engine",
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Development Status :: 4 - Beta",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Framework :: AsyncIO",
    ],    
    project_urls={
        "CI: GitHub Actions": "https://github.com/hopeit-git/hopeit.engine/actions?query=workflow",  # noqa
        "Docs: RTD": "https://hopeitengine.readthedocs.io/en/latest/",
        "GitHub: issues": "https://github.com/hopeit-git/hopeit.engine/issues",
        "GitHub: repo": "https://github.com/hopeit-git/hopeit.engine",
    },
    package_dir={
        "": "src"
    },
    packages=[
        "hopeit.app",
        "hopeit.cli",
        "hopeit.dataobjects",
        "hopeit.server",
        "hopeit.streams",
        "hopeit.testing",
        "hopeit.toolkit"
    ],
    include_package_data=True,
    package_data={
        "hopeit.app": ["py.typed"],
        "hopeit.cli": ["py.typed"],
        "hopeit.dataobjects": ["py.typed"],
        "hopeit.server": ["py.typed"],
        "hopeit.streams": ["py.typed"],
        "hopeit.testing": ["py.typed"],
        "hopeit.toolkit": ["py.typed"]
    },
    python_requires=">=3.7",
    install_requires=[ f"{lib}>={libversion(lib)}" for lib in [
        "aiojobs",
        "lz4",
        "stringcase",
        "PyJWT[crypto]",
        "deepdiff",
        "typing-inspect",
        "multidict",
        "dataclasses-jsonschema[fast-validation]",
        "fastjsonschema"
    ]],
    extras_require={
        "web": [ f"{lib}>={libversion(lib)}" for lib in [
            "aiohttp",
            "aiohttp-cors",
            "aiohttp-swagger3"
        ]],
        "cli": [ f"{lib}>={libversion(lib)}" for lib in [
            "click"
        ]],
        "redis-streams": [
            f"hopeit.redis-streams=={version['ENGINE_VERSION']}"
        ],
        "redis-storage": [
            f"hopeit.redis-storage=={version['ENGINE_VERSION']}"
        ],
        "fs-storage": [
            f"hopeit.fs-storage=={version['ENGINE_VERSION']}"
        ],
        "config-manager": [
            f"hopeit.config-manager=={version['ENGINE_VERSION']}"
        ],
        "log-streamer": [
            f"hopeit.log-streamer=={version['ENGINE_VERSION']}"
        ],
        "apps-visualizer": [
            f"hopeit.apps-visualizer=={version['ENGINE_VERSION']}"
        ],
        "apps-client": [
            f"hopeit.apps-client=={version['ENGINE_VERSION']}"
        ]
    },
    entry_points={
        "console_scripts": [
            "hopeit_server = hopeit.cli.server:server",
            "hopeit_openapi = hopeit.cli.openapi:openapi"
        ]
    }
)
