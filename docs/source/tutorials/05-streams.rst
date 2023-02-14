Process events asynchronously using STREAMS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In this tutorial we will create and run a Hopeit App or microservice
with an endpoint that publishes data to a Redis Stream, and an event
that reads data from the stream and process it, saving results to the
filesystem.

Step 1: Create virtual environment and install hopeit.engine
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Install hopeit.engine: `Installation
instructions <../quickstart/install.html>`__

Step 2: Install and start Redis
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In order to create STREAM events in your app, you need an Redis instance
or cluster. You can run Redis in docker, from ``/docker`` folder in
hopeit.engine project, using docker-compose:

::

   pip install docker-compose
   cd docker
   docker-compose up -d redis

If you prefer, you can install Redis on your own:
https://redis.io/topics/quickstart

We assume in this tutorial that redis will be accessible under
``redis://localhost:6379``

Step 3: Create App configuration json file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create a file named ``config.json`` with the following contents

.. code:: json

   {
     "app": {
       "name": "my-streaming-app",
       "version": "1.0"
     },
     "env" : {
         "process_message": {
             "save_path": "processed_messages"
         }
     },
     "events": {
       "send-message": {
         "type": "POST",
         "write_stream": {
             "name": "my-stream"
         }
       },
       "process-message": {
         "type": "STREAM",
         "read_stream": {
             "name": "my-stream",
             "consumer_group": "process-message-group"
         }
       }
     }
   }

We’ve defined 2 events:

-  send-message, a GET endpoint that will publish data to a stream named
   “my-stream”.
-  process-message, a STREAM event that will read events from
   “my-stream” and do something.

Step 4: Create a server config file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create a file named ``server.json`` with a basic configuration: for
development we will set logging level to DEBUG so our app logs
everything to the console. We also specify a connection string to Redis.

.. code:: json

   {
       "logging": {
           "log_level": "DEBUG"
       },
       "streams": {
           "connection_str": "redis://localhost:6379"
       },
       "api": {
         "docs_path": "/api/docs"
       }
   }

Step 5: Create the event handlers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Create a python module ``myapp``, this is file named ``__init__.py``
   inside a folder ``my_streaming_app``

::

   mkdir my_streaming_app
   cd my_streaming_app
   touch __init__.py

2. In the same folder, ``my_streaming_app``, now create a python file
   ``data_model.py`` with the following code

.. code:: ipython3

    """
    Data Model for my_app
    """
    from enum import Enum
    
    from hopeit.dataobjects import dataobject
    
    
    @dataobject
    class MyData:
        text: str
    
    
    class Status(Enum):
        NEW = 'NEW'
        VALID = 'VALID'
        PROCESSED = 'PROCESSED'
    
    
    @dataobject
    class MyMessage:
        text: str
        status: Status


3. In the same folder, ``my_streaming_app``, now create a python file
   ``send_message.py`` with the following code

.. code:: ipython3

    """
    Send Message:
    ===============================================
    Sends a message to be processed asynchronously
    """
    from typing import Optional, Union
    
    from hopeit.app.context import EventContext, PostprocessHook
    from hopeit.app.api import event_api
    from hopeit.app.logger import app_extra_logger
    
    from .data_model import MyData, Status, MyMessage
    
    logger, extra = app_extra_logger()
    
    __steps__ = ['create_message', 'validate']
    
    __api__ = event_api(
        payload=(MyData, "data received"),
        responses={
            200: (MyMessage, "message submitted to process"),
            400: (str, "invalid message error")
        }
    )
    
    
    async def create_message(payload: MyData, context: EventContext) -> MyMessage:
        """
        Creates MyMessage objects from the received text in MyData payload
        """
        logger.info(context, "Received data", extra=extra(length=len(payload.text)))
        message = MyMessage(payload.text, Status.NEW)
        return message
    
    
    async def validate(message: MyMessage, context: EventContext) -> Optional[MyMessage]:
        """
        Validates the lenght of the text is at least 3 characters, then set status to VALID
        and return message to be submitted to stream. If message is not valid, None is returned and
        no message is sent to stream.
        """
        if len(message.text) < 3:
            return None
        message.status = Status.VALID
        return message
    
    
    async def __postprocess__(message: Optional[MyMessage], context: EventContext,
                              response: PostprocessHook) -> Union[MyMessage, str]:
        """
        Special handler to customize what's returned as a response to the POST request received.
        Sets status to 400 if the message was invalid and returns just a message.
        Returns the validated message otherwise.
        Notice that this step can occur after MyMessage was already submitted to the stream.
        """
        if message is None:
            response.status = 400
            return "invalid data received"
        return message


Notice that we’ve introduced several new concepts:

-  ``logger, extra = app_extra_logger()`` enables us to log messages
   with proper information about the engine instance and event that is
   running, adding extra fields to the log entry. This is used in
   ``logger.info(context, "Received data", extra=extra(length=len(payload.text)))``
   to log the lenght of received texts.

-  In the class ``MyMessage`` we created a field of ``Status`` types
   that derived from python ``Enum``. When this object is read and
   converted to json proper values for Status fields will be validated.

-  We specify that our event will run two independent functions or
   steps: ``__steps__ = ['create_message', 'validate']``. Of course for
   this simple example we could do everything in the same method, but
   this shows how functions can be chained. The engine will ensure steps
   all called in order according to the datatypes that are received.

-  ``__postprocess__`` method is an special purpose method that is
   usually defined when we want to manipulate the response sent back to
   the API user. In this particular case we are filtering out messages
   with text lenght < 3 and returning None from validate function to
   avoid data to the published in ``my-stream``, but for the API user we
   defined and error message and set the response status to 400 using
   ``__postprocess__``

4. In the same folder, ``my_streaming_app``, now create a python file
   ``process_message.py`` with the following code

.. code:: ipython3

    """
    Process Message:
    ===================================================================
    Receive messages submitted to stream and saves data to disk as JSON
    """
    import uuid
    from typing import Optional, Union
    
    from hopeit.app.context import EventContext
    from hopeit.app.logger import app_extra_logger
    from hopeit.toolkit.storage.fs import FileStorage
    
    from .data_model import Status, MyMessage
    
    logger, extra = app_extra_logger()
    
    __steps__ = ['save_message']
    
    output: FileStorage = None
    
    
    async def __init_event__(context: EventContext):
        """
        Initializes output data saver using path configured in config.json
        """
        global output
        if output is None:
            save_path = context.env['process_message']['save_path']
            logger.info(context, "Initializing FileStorage...", extra=extra(path=save_path))
            output = FileStorage(path=save_path)
    
    
    async def save_message(message: MyMessage, context: EventContext) -> MyMessage:
        """
        Receives `MyMessage` from stream, updates status and saves to disk.
        """
        assert output
        logger.info(context, "Received message", extra=extra(length=len(message.text)))
        message.status = Status.PROCESSED
        key = str(uuid.uuid4())
        saved_path = await output.store(key=key, value=message)
        logger.info(context, "Message saved", extra=extra(path=saved_path))


Some of the concepts introduced:

-  ``__init__`` method is usually used to initialize database
   connections or resources that will live during the whole App
   lifecyle. ``__init__`` is usually called once per event, but this is
   not guaranteed, so it is ok to gard the execution like we did in
   ``if global is None:`` in case initialization is called more that
   once.

-  Notice that there is no ``__api__`` entry on this event, since it
   wont provide API endpoints. Instead it will listen continuously to
   events in ``my-stream`` and execute the code once per event.

Step 6: Run the server
^^^^^^^^^^^^^^^^^^^^^^

Remember that we will need a Redis instance running and listening on
localhost:6379 default port for this example to work. Check Step 2 of
this tutorial if you want to run Redis using Docker.

Go back to folder where ``my_streaming_app`` is located

::

   cd ..

Lets create openapi.json file for the first time: (If you don’t want to
enable OpenAPI schema validation, you can skip this step, and remove
``--api-file`` option when running the server)

::

   export PYTHONPATH=. && hopeit_openapi create --config-files=server.json,config.json --output-file=openapi.json
   API Version: 1.0.0
   API Title: My Streaming App
   API Description: My Streaming App Tutorial

Run hopeit server using the following command:

::

    export PYTHONPATH=. && hopeit_server run --start-streams --config-files=server.json,config.json --api-file=openapi.json

Server should be running and listening on port 8020:

::

   2020-07-02 16:36:56,288 | INFO | hopeit.engine 0.1.0 engine hostname 46299 | [hopeit.server.engine] Starting engine... | 
   ...
   2020-07-02 16:36:56,357 | INFO | hopeit.engine 0.1.0 engine hostname 46299 | [hopeit.server.engine] Starting app=my_streaming_app.1x0... | 
   2020-07-02 16:36:56,358 | INFO | hopeit.engine 0.1.0 engine hostname 46299 | [hopeit.server.streams] Connecting address=redis://localhost:6379... | 
   2020-07-02 16:36:56,361 | INFO | hopeit.engine 0.1.0 engine hostname 46299 | [hopeit.server.web] POST path=/api/my-streaming-app/1x0/send-message input=<class 'my_streaming_app.data_model.MyData'> | 
   2020-07-02 16:36:56,361 | INFO | hopeit.engine 0.1.0 engine hostname 46299 | [hopeit.server.web] STREAM path=/mgmt/my-streaming-app/1x0/process-message/[start|stop] | 
   2020-07-02 16:36:56,361 | INFO | hopeit.engine 0.1.0 engine hostname 46299 | [hopeit.server.web] STREAM start event_name=process-message read_stream=my-stream | 
   2020-07-02 16:36:56,361 | INFO | hopeit.engine 0.1.0 engine hostname 46299 | [hopeit.server.engine] Starting reading stream... | stream.app_key=my_streaming_app.1x0 | stream.event_name=process-message
   2020-07-02 16:36:56,361 | DEBUG | hopeit.engine 0.1.0 engine hostname 46299 | [hopeit.server.web] Performing forced garbage collection... | 
   2020-07-02 16:36:56,368 | INFO | hopeit.engine 0.1.0 engine hostname 46299 | [hopeit.server.streams] Consumer_group already exists read_stream=my-stream consumer_group=process-message-group | 
   2020-07-02 16:36:56,369 | INFO | hopeit.engine 0.1.0 engine hostname 46299 | [hopeit.server.engine] Consuming stream... | stream.app_key=my_streaming_app.1x0 | stream.event_name=process-message | stream.name=my-stream | stream.consumer_group=process-message-group
   ======== Running on http://0.0.0.0:8020 ========
   (Press CTRL+C to quit)

Step 7: Call the endpoint to submit some data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Lets call the endpoint with a sample JSON as payload:

::

   curl -X POST "http://localhost:8020/api/my-streaming-app/1x0/send-message" -H "Accept: application/json, application/json" -H "Content-Type: application/json" -d "{ \"text\": \"valid text\"}"

We should get as response a JSON object representing and instance of
``MyMessage``

::

   {"text": "valid text", "status": "VALID"}%

We should see in the logs information about how the request was served
successfully, in the first part we can see that ``send_message`` event
was executed and response sent back to the user:

::

   2020-07-02 16:52:35,946 | INFO | my-streaming-app 1.0 send-message hostname 48884 | START | ...| track.request_id=3bb68f7a-8f18-49b1-9af4-f3caee0eec74 | ...
   2020-07-02 16:52:35,947 | INFO | my-streaming-app 1.0 send-message hostname 48884 | Received data | extra.length=10 |...
   2020-07-02 16:52:35,958 | INFO | my-streaming-app 1.0 send-message hostname 48884 | DONE | response.status=200 | metrics.duration=12.127 | ...

Later we can see that the message sent to ``my-stream`` was consumed and
processed by ``process_message`` event:

::

   2020-07-02 16:52:36,294 | INFO | my-streaming-app 1.0 process-message hostname 48884 | START | stream.app_key=my_streaming_app.1x0 | stream.event_name=process-message | stream.name=my-stream | stream.consumer_group=process-message-group | track.request_id=3bb68f7a-8f18-49b1-9af4-f3caee0eec74 ...
   2020-07-02 16:52:36,295 | INFO | my-streaming-app 1.0 process-message hostname 48884 | Initializing FileStorage... | extra.path=processed_messages ...
   2020-07-02 16:52:36,295 | INFO | my-streaming-app 1.0 process-message hostname 48884 | Received message | extra.length=10 ...
   2020-07-02 16:52:36,301 | INFO | my-streaming-app 1.0 process-message hostname 48884 | Message saved | extra.path=processed_messages/1683ec54-20aa-4263-95ab-2b8d102b0329.json ...
   2020-07-02 16:52:36,303 | INFO | my-streaming-app 1.0 process-message hostname 48884 | DONE | ... | track.request_id=3bb68f7a-8f18-49b1-9af4-f3caee0eec74 | ...
   2020-07-02 16:52:36,303 | INFO | my-streaming-app 1.0 process-message hostname 48884 | STATS | metrics.stream.total_consumed_events=1 | metrics.stream.total_errors=0 | metrics.stream.avg_rate=104.123 | ...

We can see that a file with a random name was saved under the configured
folder, lets check it contents (notice that the file name could vary):

::

   cat processed_messages/1683ec54-20aa-4263-95ab-2b8d102b0329.json

   {"text": "valid text", "status": "PROCESSED"}

One interesting concept here is that both parts of the processing
``send_message`` and ``process_message`` that have happened
asynchronously and in a distributed environment they can be handled by
different instances of the app, they share the same ``request_id`` in
the logs, and is the same request_id that is returned to the user as a
response header. This way we can track and trace the whole lifecycle and
processing of our data, even if it happens at different points in time.

We can see also that the engine will log STATS entries with information
about a running STREAM event, in order to proper monitor how are they
working.

Streams management
^^^^^^^^^^^^^^^^^^

In addition to the regular API endpoints, hopeit.engine provides
management endpoint to start/stop streams.

You can stop stream processing for ``process_message`` event using:

::

   curl -i localhost:8020/mgmt/my-streaming-app/1x0/process-message/stop

And you can restart execution using

::

   curl -i localhost:8020/mgmt/my-streaming-app/1x0/process-message/start

When restarting execution, all unconsumed events in Redis will be
processed. Activity about stopping and starting stream process will be
logged.

