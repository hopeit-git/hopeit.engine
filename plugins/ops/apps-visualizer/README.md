# hopeit.engine apps-visualizer plugin


This library is part of hopeit.engine:

> check: https://github.com/hopeit-git/hopeit.engine


### Install using hopeit.engine extras [apps-visualizer]:

```
pip install hopeit.engine[apps-visualizer]
```

### Include plugin configuration file when running `hopeit_server` in addition to your existing config files.

```
hopeit_server ... --config-files=...,plugins/ops/apps-visualizer/config/plugin-config.json,...
```

### Visualize App events diagram using url:

```
http://host:port/ops/apps-visualizer
```

### To enable Live! events activity visualization, configure and start an instance of `log-streamer`:
 
#### Copy `config/plugin-config.json` and customize parameters to match your runtime environment. 


#### Run a `hopeit_server` instance with log_streamer, in each node where you run your appplications:
```
hopeit_server --port=8099 --start-streams --config-files=server-config.json,customized-plugin-config.json
```

> Now when you can switch from `Static` to `Live` view clicking on the label at the top right of the Apps Visualizer page
