"""
Engine version constants.
Increment on release

To ensure configuration files from example apps and plugins have same version as engine,
an environment variable `HOPEIT_ENGINE_VERSION`
"""
import os
import sys

ENGINE_NAME = "hopeit.engine"
ENGINE_VERSION = "0.3.0rc8"

# Major.Minor version to be used in App versions and Api endpoints for Apps/Plugins
APPS_API_VERSION = '.'.join(ENGINE_VERSION.split('.')[0:2])

os.environ['HOPEIT_ENGINE_VERSION'] = ENGINE_VERSION
os.environ['HOPEIT_APPS_API_VERSION'] = APPS_API_VERSION

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "APPS_API_VERSION":
        print(APPS_API_VERSION)
    else:
        print(ENGINE_VERSION)
