"""
Engine version constants.
Increment on release

To ensure configuration files from example apps and plugins have same version as engine,
an environment variable `HOPEIT_ENGINE_VERSION` 

"""
import os

ENGINE_NAME = "hopeit.engine"
ENGINE_VERSION = "0.3.0rc4"

os.environ['HOPEIT_ENGINE_VERSION'] = ENGINE_VERSION

if __name__ == "__main__":
    print(ENGINE_VERSION)
