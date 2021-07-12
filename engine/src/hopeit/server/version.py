"""
Engine version constants.
Increment on release
To ensure configuration files from example apps and plugins have same version as engine,
environment variables `HOPEIT_ENGINE_VERSION` and `HOPEIT_APPS_API_VERSION` are set.
"""
import os
import sys

ENGINE_NAME = "hopeit.engine"
ENGINE_VERSION = "0.9.3"

# Major.Minor version to be used in App versions and Api endpoints for Apps/Plugins
APPS_API_VERSION = '.'.join(ENGINE_VERSION.split('.')[0:2])
APPS_ROUTE_VERSION = APPS_API_VERSION.replace('.', 'x')

os.environ['HOPEIT_ENGINE_VERSION'] = ENGINE_VERSION
os.environ['HOPEIT_APPS_API_VERSION'] = APPS_API_VERSION
os.environ['HOPEIT_APPS_ROUTE_VERSION'] = APPS_ROUTE_VERSION

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "APPS_API_VERSION":
        print(APPS_API_VERSION)
    elif len(sys.argv) > 1 and sys.argv[1] == "APPS_ROUTE_VERSION":
        print(APPS_ROUTE_VERSION)
    else:
        print(ENGINE_VERSION)
