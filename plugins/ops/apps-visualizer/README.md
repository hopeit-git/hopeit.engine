# hopeit.engine apps-visualizer plugin


This library is part of hopeit.engine:

> check: https://github.com/hopeit-git/hopeit.engine


### Install using hopeit.engine extras [apps-visualizer]:

```
pip install hopeit.engine[apps-visualizer]
```

### Include config-manager plugin config file when running `hopeit_server` in addition to your existing config files for each process/server that needs to be monitored.

```
hopeit_server --port=8020 --config-files=server-config.json,plugins/ops/config-manager/config/plugin-config.json,my-app-config.json
```

### Export list of hosts to connect to, and run a new hopeit_server instance with apps-visualizer plugin

```
export HOPEIT_APPS_VISUALIZER_HOSTS="http://host:8020,in-process"

hopeit_server --port=8098 --config-files=server-config.json,plugins/ops/apps-visualizer/config/plugin-config.json --api-file=plugins/ops/apps-visualizer/api/openapi.json
```

> The first host in the list, specifies to monitor apps running in `http://host:8020` by connecting in intervals to the server through config-manager plugin endpoints.

> Using `in-process` as host name local process running apps-visualizer can be monitored also without network load.

> Instead of using an environment variable, list of hosts can be directly added to a customized version of plugin-config.json


### Visualize App events diagram using url:

```
http://host:8098/ops/apps-visualizer
```

### To enable Live! events activity visualization, configure and start an instance of `log-streamer`:
 
#### Copy `config/plugin-config.json` and customize parameters to match your runtime environment. 


#### Run a `hopeit_server` instance with log_streamer, in each node where you run your applications:
```
hopeit_server --port=8099 --start-streams --config-files=server-config.json,customized-plugin-config.json
```

> Now when you can switch from `Static` to `Live` view clicking on the label at the top right of the Apps Visualizer page

If you want also to monitor log-streamer app, you can set:

```
export HOPEIT_APPS_VISUALIZER_HOSTS=$HOPEIT_APPS_VISUALIZER_HOSTS,http://host:8099
```

and re-run apps-visualizer using `hopeit_server` command above.
