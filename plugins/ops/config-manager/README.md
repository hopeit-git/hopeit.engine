# hopeit.engine config-manager plugin


This library is part of hopeit.engine:

> check: https://github.com/hopeit-git/hopeit.engine


### Install using hopeit.engine extras [config-manager]:

```
pip install hopeit.engine[config-manager]
```

### Include plugin configuration file when running `hopeit_server` in addition to your existing config files. 

```
hopeit_server ... --config-files=...,plugins/ops/config-manager/config/plugin-config.json,...
```

> Remember also to include the plugin config file, when using `hopeit_openapi` command line tool to create or update Open API spec file for your server

### Check added endpoints under Config Manager session:

```
http://host:port/api/docs
```
