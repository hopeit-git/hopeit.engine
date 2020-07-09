Run example application
=======================

1 - To run simple-example application included in this repo you need to install hopeit.engine, basic-auth plugin and the simple-example application. Also a local instance of redis is required to be up.

.. code-block:: bash

 make install
 make PLUGINFOLDER=plugins/auth/basic-auth/ install-plugin
 make APPFOLDER=apps/examples/simple-example/ install-app

 cd docker
 docker-compose up -d redis
 cd ..

 hopeit_engine run --port=8020 --start-streams ----config-files=engine/config/dev-local.json,plugins/auth/basic-auth/config/1x0.json,apps/examples/simple-example/config/1x0.json --api-file=apps/examples/simple-example/api/openapi.json


2 - To run and debug using VSCode, add this configuration to your .launch.json file:

.. code-block:: json 

 {
    "version": "0.2.0",
    "configurations": [ 
        {
            "name": "simple-example",
            "type": "python",
            "request": "launch",
            "module": "hopeit.server.web",
            "console": "integratedTerminal",
            "args": [
                "--port=8020", 
                "--start-streams", 
                "--config-files=engine/config/dev-local.json,plugins/auth/basic-auth/config/1x0.json,apps/examples/simple-example/config/1x0.json",
                "--api-file=apps/examples/simple-example/api/openapi.json"
            ],
            "cwd": "${workspaceFolder}"
        }
    ]
 }
