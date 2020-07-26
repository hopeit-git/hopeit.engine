import setuptools


setuptools.setup(
    name="hopeit.plugins.redis_mon",
    version="0.1.0",
    description="Hopeit.py Redis Monitoring Plugin",
    package_dir={
        "": "src"
    },
    packages=[
        "hopeit.redis_mon"
    ],
    include_package_data=True,
    python_requires=">=3.7",
    install_requires=[
        "hopeit.engine",
        "watchdog"
    ],
    extras_require={
    },
    entry_points={
    }
)
