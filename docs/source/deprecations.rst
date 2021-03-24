Deprecations
============

Module: hopeit.app.api
______________________

0.2.0
-----

Starting hopeit.engine version 0.1.4 event_api method add alternatives to ``title`` parameter.

Since version 0.1.4 method adds ``summary`` and ``description`` params:

.. code:: python3

    def event_api(title: Optional[str] = None,
                ...
                summary: Optional[str] = None,
                description: Optional[str] = None
                ) -> Callable[..., dict]:

From version 0.2.0 ``title`` is removed, use ``summary`` instead. Stariting this version method will require named args for all parameters:

.. code:: python3

    def event_api(*, summary: Optional[str] = None,
                description: Optional[str] = None,
                ...      
                ) -> Callable[..., dict]: