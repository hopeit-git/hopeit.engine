Create your first App
~~~~~~~~~~~~~~~~~~~~~

In this tutorial we will create and run a Hopeit App or microservice
that has a REST endpoint that returns and object built from provided
query arguements.

Step 1: Create virtual environment and install hopeit.engine
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Install hopeit.engine: `Installation
instructions <../quickstart/install.html>`__

Step 2: Create App configuration json file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create a file named ``config.json`` with the following contents

.. code:: json

   {
     "app": {
       "name": "my-app",
       "version": "1.0"
     },
     "env" : {},
     "events": {
       "sample-endpoint": {
         "type": "GET"
       }
     }
   }

Step 3: Create a server config file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create a file named ``server.json`` with a basic configuration: for
development we will set logging level to DEBUG so our app logs
everything to the console.

.. code:: json

   {
       "logging": {
           "log_level": "DEBUG"
       }
   }

Step 4: Create the event handler
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Create a python module ``myapp``: create an empty file named
   ``__init__.py`` inside a folder ``my_app``, i.e.:

::

   mkdir my_app
   cd my_app
   touch __init__.py

2. In the same folder, ``my_app``, now create a python file
   ``sample_endpoint.py`` with the following code

.. code:: ipython3

    from hopeit.app.context import EventContext
    from hopeit.dataobjects import dataobject
    
    __steps__ = ['step1']
    
    
    @dataobject
    class MyObject:
        text: str
        length: int
    
    
    async def step1(payload: str, context: EventContext) -> MyObject:
        """
        Receives a string and returns MyObject where name is the received string
        uppercased and number its length
        """
        text = payload.upper()
        length = len(payload)
        return MyObject(text, length)


Step 5: Run the server
^^^^^^^^^^^^^^^^^^^^^^

Go back to folder where ``my_app`` is located

::

   cd ..

Run hopeit server using the following command:

::

   export PYTHONPATH=. && hopeit_server run --config-files=server.json,config.json

Server should be running and listening on port 8020:

::

   2020-06-25 16:35:52,120 | INFO | hopeit.engine 0.1.0 engine hostname 15394 | [hopeit.server.engine] Starting engine... | 
   ...
   2020-06-25 16:35:52,148 | INFO | hopeit.engine 0.1.0 engine hostname 15394 | [hopeit.server.engine] Starting app=my_app.1x0... | 
   2020-06-25 16:35:52,150 | INFO | hopeit.engine 0.1.0 engine hostname 15394 | [hopeit.server.web] GET path=/api/my-app/1x0/sample-endpoint | 
   ======== Running on http://0.0.0.0:8020 ========
   (Press CTRL+C to quit)

Step 6: Call the endpoint
^^^^^^^^^^^^^^^^^^^^^^^^^

Lets call the endpoint with a sample string as payload:

::

   curl -i "localhost:8020/api/my-app/1x0/sample-endpoint?payload=hopeit"

We should get as response a JSON object representing and instance of
``MyObject``

::

   HTTP/1.1 200 OK
   X-Track-Operation-Id: 19d1311a-08b3-4fc4-ba96-b85e306e694b
   X-Track-Request-Id: 050e1e58-2e92-46a5-aff3-4f2ee3d4e2ec
   X-Track-Request-Ts: 2020-06-20T22:02:10.116858+00:00
   Content-Type: application/json
   Content-Length: 31
   Date: Sat, 20 Jun 2020 22:02:10 GMT

   {"name": "HOPEIT", "number": 6}%

We should see in the logs information about how the request was served
successfully:

::

   2020-06-25 16:38:25,528 | INFO | my-app 1.0 sample-endpoint hostname 15394 | START | track.operation_id=ca9aa13c-017b-4698-aade-cac9519d9ee7 | track.request_id=470cca74-4fb2-4e25-8da9-07acc9d0909f | track.request_ts=2020-06-25T16:38:25.528680+00:00
   2020-06-25 16:38:25,534 | INFO | my-app 1.0 sample-endpoint hostname 15394 | DONE | response.status=200 | metrics.duration=5.506 | track.operation_id=ca9aa13c-017b-4698-aade-cac9519d9ee7 | track.request_id=470cca74-4fb2-4e25-8da9-07acc9d0909f | track.request_ts=2020-06-25T16:38:25.528680+00:00

Basic terminology
^^^^^^^^^^^^^^^^^

-  **App**: is the service we just created consisting of a configuration
   file plus a python module ``my_app``.
-  **Event**: is the basic execution unit that is triggered when an
   endpoint is invoked, or a object is received from a stream. Our event
   is configured under ``events`` section in ``config.json`` and
   implemented in ``sample_endpoint.py`` file.
-  **Server**: is the instance of the microservice that is run using a
   server and one or many apps configuration files, plus their
   implementing modules. Notice that a service can consist of one or
   more Apps running under the same process.

What we have done so far?
^^^^^^^^^^^^^^^^^^^^^^^^^

We basically created a very basic microservice, with a HTTTP endpoint,
``/api/my-app/1x0/sample-endpoint`` that receives a query argument
called ``payload`` and returns an JSON object containing two fields
``text`` and ``length``.

What *hopeit.engine* did for us:

-  Registered our python file ``sample_endpoint.py`` as the handler for
   the route \`\ ``/api/my-app/1x0/sample-endpoint``
-  Runs our (micro)service backed by ``aiohttp``
-  Maps and validate the data types for the query arguments
-  Maps and validate data types, between our data objects ``MyObject``
   and the JSON response sent back
-  Adds logging to our service
-  Added a ``request_id``, ``operation_id`` and request timestamp thet
   are automatically logged and returned in the response. Hopeit.engine
   will also track requests ids among many different events if we use
   distributed processing via STREAMS (\* see tutorials below).
-  Compute execution metrics for the calls to the endpoint, metrics are
   logged by default.

What’s next?
^^^^^^^^^^^^

These are just the basics, in the next tutorials you will see:

-  `Add Open API specification to your service <02-open-api.html>`__
-  `Send data to a STREAM, backed by Redis and process the objects
   asynchronously <05-streams.html>`__
