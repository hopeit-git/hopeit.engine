from setuptools import setup

version = {}
with open("src/hopeit/server/version.py") as fp:
    exec(fp.read(), version)
    ENGINE_VERSION = version["ENGINE_VERSION"]

setup(
    install_requires=[
        "pydantic>=2.9.1,<3",
        "stringcase>=1.2.0",
        "lz4>=4.3.2",
        "PyJWT[crypto]>=2.9.0",
        "deepdiff",
        "typing-inspect",
        "multidict",
    ],
    extras_require={
        "web": [
            "aiohttp>=3.9.0,<4",
            "aiohttp-cors",
            "aiohttp-swagger3>=0.8.0",
            "gunicorn",
        ],
        "cli": ["click"],
        "redis-streams": [f"hopeit.redis-streams=={ENGINE_VERSION}"],
        "redis-storage": [f"hopeit.redis-storage=={ENGINE_VERSION}"],
        "fs-storage": [f"hopeit.fs-storage=={ENGINE_VERSION}"],
        "config-manager": [f"hopeit.config-manager=={ENGINE_VERSION}"],
        "log-streamer": [f"hopeit.log-streamer=={ENGINE_VERSION}"],
        "apps-visualizer": [f"hopeit.apps-visualizer=={ENGINE_VERSION}"],
        "apps-client": [f"hopeit.apps-client=={ENGINE_VERSION}"],
        "dataframes": [f"hopeit.dataframes=={ENGINE_VERSION}"],
    },
)
