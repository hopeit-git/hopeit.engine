import setuptools

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
    install_requires=[
        "aiojobs",
        "aiofiles",
        "aioredis",
        "lz4",
        "stringcase",
        "cryptography",
        "pyjwt[crypto]>=1.7.0,<2",
        "click",
        "deepdiff",
        "typing_inspect",
        "idna<3,>=2.5"
    ],
    extras_require={
        "web": [
            "aiohttp",
            "aiohttp_cors",
            "aiohttp-swagger3",
            "dataclasses-jsonschema[fast-validation]",
            "fastjsonschema"
        ],
        "cli": [
            "dataclasses-jsonschema[fast-validation]",
            "fastjsonschema"
        ]
    },
    entry_points={
        "console_scripts": [
            "hopeit_server = hopeit.cli.server:server",
            "hopeit_openapi = hopeit.cli.openapi:openapi"
        ]
    }
)
