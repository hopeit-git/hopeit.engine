Install hopeit.engine
=====================

The following will install core hopeit.engine componentes plus the dependencies to create an run a web server with Open
API support and the Command Line interface tools to run a server and manage APIs.

hopeit.engine requires:

* Python 3.9.x or above

1 - To install hopeit.engine with web server and command line interface support using pip on a virtual environment:

.. code-block:: bash

 python -m venv venv
 source venv/bin/activate
 pip install "hopeit.engine"
 pip install "hopeit.engine[web]"
 pip install "hopeit.engine[cli]"

2 - Optionally to enable Redis Streams, a plugin needs to be installed:

.. code-block:: bash

 pip install "hopeit.engine[redis-streams]"


3 - To install in development mode (linked to source):

.. code-block:: bash

 python -m venv venv
 source venv/bin/activate
 git clone https://github.com/hopeit-git/hopeit.engine.git
 cd hopeit.engine
 make install

