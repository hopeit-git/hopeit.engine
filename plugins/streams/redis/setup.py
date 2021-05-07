import setuptools

version = {}
with open("../../../engine/src/hopeit/server/version.py") as fp:
    exec(fp.read(), version)

setuptools.setup(
    name="hopeit.plugins.redis-streams",
    version=version['ENGINE_VERSION'],
    description="Hopeit.py Redis Streams Plugin",
    package_dir={
        "": "src"
    },
    packages=[
        "hopeit.redis_streams"
    ],
    include_package_data=True,
    python_requires=">=3.7",
    install_requires=[
        "hopeit.engine",
        "aioredis"
    ],
    extras_require={
    },
    entry_points={
    }
)
