# hopeit.engine log-streamer plugin


This library is part of hopeit.engine:

> check: https://github.com/hopeit-git/hopeit.engine


### Install using hopeit.engine extras [log-streamer]:

```
pip install hopeit.engine[log-streamer]
```

### Copy `config/plugin-config.json` and customize parameters to match your runtime environment. 


### Run a `hopeit_server` instance, in each node where you run your appplications:

```
hopeit_server --port=8099 --start-streams --config-files=server-config.json,customized-plugin-config.json
```

> This way log_streamer plugin process will run separately from your main application, read logs locally on each node and publish data to a stream.
