## hopeit.engine

Docs: https://hopeitengine.readthedocs.io/en/latest/


### Engine development README

#### Install locally for apps or plugins development:
- Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Run from hopeit.engine project root
```
    make dev
```
- Now everything you need is installed in .venv/
- Then you can create your apps or plugins and run the server

#### Install from Python Package Index
Install core hopeit.engine lib:
```
pip install "hopeit.engine"
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
    --start-streams: indicates to automatically start events of type STREAM when starting server
    
```

- Example starting a single app that depends on plugins:
```
    python engine/server/web.py --config-files=server-config.json,plugin-folder/config/plugin-config.json,app-folder/config/app-config.json
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

- To fromat code
```
    make format
```

- To run static code checks (types, style)
```
    make lint
```

- To create distribution library (hopeit.engine)
```
    make dist
```
