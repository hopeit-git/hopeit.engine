"""
hopeit engine server modules

Modules Overview:

    * **api**: provides openapi support for endpoints defined in web module.
    * **web**: provides /api endpoints creation for GET and POST events, and provides
      /mgmt endpoints for STREAM and SERVICE events
    * **engine**: provides App initialization and containers
    * **events**: provides handlers for execution of App Events
    * **streams**: provides read-write support for Redis Streams
    * **steps**: helpers to execute event steps
    * **config**: helpers to load configuration files
    * **imports**: helpers to import App Events modules
    * **logger**: provides base logging for server
    * **metrics**: provides metrics calculation for events
    * **names**: helpers for events and route naming conventions
    * **errors**: helpers for error messages
"""
__all__ = ['config',
           'engine',
           'errors',
           'events',
           'imports',
           'logger',
           'metrics',
           'names',
           'steps',
           'web',
           'api']
