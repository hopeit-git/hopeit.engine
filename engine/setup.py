from setuptools import setup

DEPS = "requirements.txt"

version = {}
with open("src/hopeit/server/version.py") as fp:
    exec(fp.read(), version)


def extract_package_names(file_path):
    """Extract package names from a requirements.txt file."""
    package_names = set()
    with open(file_path, "r") as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith("#"):
                pkg_name = (
                    line.split("==")[0]
                    .split(">=")[0]
                    .split("<=")[0]
                    .split(">=")[0]
                    .split(">")[0]
                    .split("<")[0]
                    .split(";")[0]
                    .strip()
                )
                package_names.add(pkg_name)
    return package_names


def match_packages(file_path, packages_to_match):
    """Return package names from the file that match the given list."""
    all_packages = extract_package_names(file_path)
    matches = [pkg for pkg in packages_to_match if pkg in all_packages]
    return matches


setup(
    install_requires=match_packages(
        DEPS,
        [
            "lz4",
            "stringcase",
            "PyJWT[crypto]",
            "deepdiff",
            "typing-inspect",
            "multidict",
            "pydantic",
        ],
    ),
    extras_require={
        "web": match_packages(DEPS, ["aiohttp", "aiohttp-cors", "aiohttp-swagger3", "gunicorn"]),
        "cli": match_packages(DEPS, ["click"]),
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
