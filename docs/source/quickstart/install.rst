Install hopeit.engine
=====================

The following will install core hopeit.engine componentes plus the dependencies to create an run a web server with Open
API support and the Command Line interface tools to run a server and manage APIs.

hopeit.engine requires:

* Python 3.7.x or above

1 - To install hopeit.engine with web server and command line interface support from source using a virtual environment:

.. code-block:: bash

 python -m venv venv
 source venv/bin/activate
 git clone https://github.com/hopeit-git/hopeit.engine.git
 cd hopeit.engine
 make dist-only
 cd engine/dist
 pip install "hopeit.engine-0.1.0-py3-none-any.whl"
 pip install "hopeit.engine-0.1.0-py3-none-any.whl[web]"
 pip install "hopeit.engine-0.1.0-py3-none-any.whl[cli]"

2 - To install in development mode (linked to source):

.. code-block:: bash

 python -m venv venv
 source venv/bin/activate
 git clone https://github.com/hopeit-git/hopeit.engine.git
 cd hopeit.engine
 make install

