import setuptools

version = {}
with open("../../../engine/src/hopeit/server/version.py") as fp:
    exec(fp.read(), version)

setuptools.setup(
    version=version["ENGINE_VERSION"],
    url="https://github.com/hopeit-git/hopeit.engine",
    project_urls={
        "CI: GitHub Actions": "https://github.com/hopeit-git/hopeit.engine/actions?query=workflow",
        "Docs: RTD": "https://hopeitengine.readthedocs.io/en/latest/",
        "GitHub: issues": "https://github.com/hopeit-git/hopeit.engine/issues",
        "GitHub: repo": "https://github.com/hopeit-git/hopeit.engine",
    },
    packages=["hopeit.config_manager"],
    install_requires=[f"hopeit.engine[web]=={version['ENGINE_VERSION']}"],
)
