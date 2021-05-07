Run with Redis Streams
======================

1 - Install hopeit.engine using [redis-streams] plugin extras:

.. code-block:: bash

 pip install "hopeit.engine[redis-streams]"


2 - Setup configuration: add a stream_manager entry in server config json file:

.. code-block:: json

  "streams": {
    "stream_manager": "hopeit.redis_streams.RedisStreamManager",
    "connection_str": "redis://localhost:6379"
  }


3 - Start a Redis server, i.e with docker:

.. code-block:: bash
 
 pip install docker-compose
 cd docker/
 docker-compose up redis

