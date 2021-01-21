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
        "Development Status :: 4 - Beta",
        "Operating System :: POSIX",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Topic :: Internet :: WWW/HTTP",
        "Framework :: AsyncIO",
    ],
    license="Apache 2",
    package_dir={
        "": "src"
    },
    project_urls={
        "CI: GitHub Actions": "https://github.com/hopeit-git/hopeit.engine/actions?query=workflow",  # noqa
        "Docs: RTD": "https://hopeitengine.readthedocs.io/en/latest/",
        "GitHub: issues": "https://github.com/hopeit-git/hopeit.engine/issues",
        "GitHub: repo": "https://github.com/hopeit-git/hopeit.engine",
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
        "pyjwt[crypto]>=1.7.0,<2",
        "click",
        "deepdiff",
        "typing_inspect",
        "idna<3,>=2.5"
    ],
>>>>>>> add summary to method api
    extras_require={
        "web": [ f"{lib}=={libversion(lib)}" for lib in [
            "aiohttp",
            "aiohttp-cors",
            "aiohttp-swagger3",
            "dataclasses-jsonschema[fast-validation]",
            "fastjsonschema"
<<<<<<< HEAD
        ]],
        "cli": [ f"{lib}=={libversion(lib)}" for lib in [
            "dataclasses-jsonschema[fast-validation]",
            "fastjsonschema"
        ]]
=======
        ],
        "cli": [
            "dataclasses-jsonschema[fast-validation]",
            "fastjsonschema"
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
