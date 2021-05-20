## hopeit.engine

Docs: https://hopeitengine.readthedocs.io/en/latest/


### Engine development README

#### Install locally for apps or plugins development:
- Install Python 3.8, recommended (you can use 3.7 to 3.9)
- Create and activate a virtual environment (recommended)
- Run from hopeit.engine project root
```
    make dev-deps && make install
```
- Now hopeit.engine package should be installed into your virtual/conda env linked to the source code in ./src
- Then you can create your apps or plugins and run the server

#### Install from Python Package Index

- Install Python 3.8, recommended (you can use 3.7 to 3.9)
- Create and activate a virtual environment (recommended)
- Install hopeit.engine

Install core hopeit.engine lib:
```
pip install "hopeit.engine"
```
Install extras needed to run as a server and command line tools:
```
pip install "hopeit.engine[web,cli]"
```

#### Configure
- Create server configuration json file
    - See [configuration examples](./config/)
- Create apps configuration and python files
    - See [apps examples](../apps/examples/)
- Optionally you can develop plugins, similar to apps but can be shared
    - See available [plugins](../plugins/)

#### Start http server
- Example starting a single app/microservice
```
    python -m hopeit.server.web --config-files=server-config.json,app-folder/config/app-config.json
```

- Additional options:
```
    --config-files: comma-separated file of config files to load, starting with server config, then plugins, then apps
    --api-file: path to openapi complaint json specification
    --host: server host address or name, default is --host=0.0.0.0
    --port: indicates to listen on another port number, default is --port=8020
    --path: indicates to listen in a unix socket path, default is disabled    
    --start-streams: indicates to auomatically start events of type STREAM when starting server
    
```

- Example starting a single app that depends on plugins:
```
    python engine/server/web.py --config-files=server-config.json,plugin-foler/config/plugin-config.json,app-folder/config/app-config.json
```

### Tools for Engine Development

- To install development dependencies, from engine folder run:
```
    make dev
```

- To run tests
```
    make test
```

- To run static code checks (types, style)
```
    make check
```

- To create distribution library (hopeit.engine)
```
    make dist
```

- To install engine in local python environment
```
    make install
```

- Examples: to install plugin or app in virtual environment
    - to use existing app and plugins, you will need to obtain also a configuration file for each app and plugin. install-app will only install source code.
```
    make PLUGINFOLDER=plugins/auth/basic-auth install-plugin
    make APPFOLDER=apps/examples/simple-example install-app
```
