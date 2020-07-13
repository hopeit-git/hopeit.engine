"""
hopeit.engine testing module

Provides utilities to test and write unit or integration tests for App Events:

    * **apps**: load config and execute app events for testing behaviour. Allows execution
      of events without starting a server.
    * **encryption**: provides data encryption for tests. Useful to test data apps.
"""
__all__ = ['apps',
           'encryption']
