Add OpenAPI to your first App
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In this document we will add to the Hopeit App created in the previous
tutorial the abiliy to validate, and generate API docs through the Open
API feature supported by hopeit.engine.

Also you’ll see how to access the web interface which hopeit.engine
provides out of the box, to visualize the your API docs and interact
with your endpoints directly.

\*You can use the same files created on the previous tutorial and jump
to [Step 5: Adds OpenAPI json-schema validation and API docs]

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

1. Create a python module ``myapp``, this is file named ``__init__.py``
   inside a folder ``my_app``

::

   mkdir my_app
   cd my_app
   touch __init__.py

2. In the same folder, ``my_app``, now create a python file
   ``sample_endpoint.py`` with the following code

Step 5: Add OpenAPI json-schema validation and API docs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To add Open API support to your endpoints, add a description header, and
an ``__api__`` definition to your source file:

.. code:: ipython3

    """
    API: sample-endpoint
    ---------------------------------------------------
    Same as first app sample-endpoint now with Open API.
    
    This endpoint adds the capability of json-schema validation and API docs.
    [CommonMark syntax](http://spec.commonmark.org/)  MAY be used for rich text
    representation.
    """
    
    from hopeit.app.api import event_api
    from hopeit.app.context import EventContext
    from hopeit.dataobjects import dataobject
    
    __steps__ = ['step1']
    
    
    @dataobject
    class MyObject:
        text: str
        length: int
    
    
    __api__ = event_api(
        summary="Sample Endpoint",
        query_args=[('payload', str, "provide a 'string' to create 'MyObject'"),
                    ('number', int, "number to be added to the 'length' of the payload of MyObject")],
        responses={
            200: (MyObject, "MyObject where name is the received string uppercased and number its length")
        }
    )
    
    
    async def step1(payload: str, context: EventContext, number: str) -> MyObject:
        text = payload.upper()
        length = len(payload) + int(number)
        return MyObject(text, length)


Adding the ``__api__`` entry, enables to define the specifications of
``query_args``, as well as the different types of ``responses`` provided
by the endpoint. For this pourpose, ``event_api`` method is provided as
a convenient way to define Open API specification from your source code
file. If for some reason this helper doesn’t suit to your needs, you
could allways write the entire definition of the endpoint as a python
``dict`` following the OpenAPI standard. *CommonMark syntax MAY be used
for rich text representation.*

Finally, in order to obtain the ``openapi.json`` file run from the root
of the project:

.. code:: bash

   export PYTHONPATH=./ && hopeit_openapi create --config-files=server.json,config.json --api-version=1.0.1 --title="Sample endpoint" --description="sample-endpoint app with OpenAPI validation and API docs" --output-file=api/openpai.json

Now you can run the app with OpenAPI enabled

.. code:: bash

   export PYTHONPATH=./ && hopeit_server run --config-files=server.json,config.json --api-file=api/openpai.json

Step 6: Enable OpenAPI documentation page:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We are almost there, this is the last step to finaly browse the docs in
you favorite web browser. Add to the config file ``server.json`` the api
section to set the path for the API docs.

.. code:: json

   {
       "logging": {
           "log_level": "DEBUG"
       },
       "api": {
           "docs_path": "/api/docs"
       }
   }

Now you can run your app with json-schema validation and API docs
enabled in ``/api/docs``:

.. code:: bash

   export PYTHONPATH=./ && hopeit_server ---files=server.json,config.json --api-file=api/openpai.json

Done! point your browser to http://localhost:8020/api/docs

Step 6: Call the endpoint from API Docs page:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#TODO: Add snapshot

