from setuptools import setup
import re

DEPS = "requirements.txt"

version = {}
with open("src/hopeit/server/version.py") as fp:
    exec(fp.read(), version)


def read_requirements_txt(*packages):
    """Return lines from the file that match the exact package names with optional version specifiers."""
    matches = []
    package_patterns = [
        re.compile(rf"^{re.escape(package)}(\s|==|>=|<=|>|<|;|$)", re.IGNORECASE)
        for package in packages
    ]

    with open(DEPS, "r") as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith("#"):
                if any(pattern.match(line) for pattern in package_patterns):
                    matches.append(line)
    return matches


setup(
    install_requires=read_requirements_txt(
        "lz4",
        "stringcase",
        "PyJWT[crypto]",
        "deepdiff",
        "typing-inspect",
        "multidict",
        "pydantic",
    ),
    extras_require={
        "web": read_requirements_txt("aiohttp", "aiohttp-cors", "aiohttp-swagger3", "gunicorn"),
        "cli": read_requirements_txt("click"),
        "redis-streams": [f"hopeit.redis-streams=={version['ENGINE_VERSION']}"],
        "redis-storage": [f"hopeit.redis-storage=={version['ENGINE_VERSION']}"],
        "fs-storage": [f"hopeit.fs-storage=={version['ENGINE_VERSION']}"],
        "config-manager": [f"hopeit.config-manager=={version['ENGINE_VERSION']}"],
        "log-streamer": [f"hopeit.log-streamer=={version['ENGINE_VERSION']}"],
        "apps-visualizer": [f"hopeit.apps-visualizer=={version['ENGINE_VERSION']}"],
        "apps-client": [f"hopeit.apps-client=={version['ENGINE_VERSION']}"],
        "dataframes": [f"hopeit.dataframes=={version['ENGINE_VERSION']}"],
    },
)
