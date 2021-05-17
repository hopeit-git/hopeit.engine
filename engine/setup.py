import setuptools

version = {}
with open("src/hopeit/server/version.py") as fp:
    exec(fp.read(), version)

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
        ]
    },
    entry_points={
        "console_scripts": [
            "hopeit_server = hopeit.cli.server:server",
            "hopeit_openapi = hopeit.cli.openapi:openapi"
        ]
    }
)
