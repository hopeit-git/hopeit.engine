Deprecations
============

Module: hopeit.app.api
______________________

Deprecation warning: 
Starting hopeit.engine version 0.1.4 event_api method will deprecate ``title`` parameter and will be remove in 0.2.0, use ``summary`` instead.

Since version 0.1.4 method adds ``summary`` and ``description`` params:

.. code:: python3

    def event_api(title: Optional[str] = None,
                payload: Optional[PayloadDef] = None,
                query_args: Optional[List[ArgDef]] = None,
                responses: Optional[Dict[int, PayloadDef]] = None, *,
                summary: Optional[str] = None,
                description: Optional[str] = None
                ) -> Callable[..., dict]:

From version 0.2.0 'title' will be removed, use ``summary`` instead. Stariting this version method will require named args for all parameters:

.. code:: python3

    def event_api(*, summary: Optional[str] = None,
                description: Optional[str] = None,
                payload: Optional[PayloadDef] = None,
                query_args: Optional[List[ArgDef]] = None,
                responses: Optional[Dict[int, PayloadDef]] = None              
                ) -> Callable[..., dict]: