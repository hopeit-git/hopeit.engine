# hopeit.engine apps-client plugin


This library is part of hopeit.engine:

> check: https://github.com/hopeit-git/hopeit.engine


### Install using hopeit.engine extras [apps-client]:

```
pip install hopeit.engine[apps-client]
```

### Config app_connection section in your app to use this client implementation:

Configre a connection in `app_connections` section and specify which events to invoke
inside `event.connections` section:

```
    ...
    "app_connections": {
        "target-app-conn": {
            "name": "target-app",
            "version": "1.0",
            "client": "hopeit.apps_client.AppsClient"
        }
    },
    ...

    "events": {
        "my-event": {
            ...
            "connections": [
                {
                    "app_connection": "target-app-conn",
                    "event": "target-event",
                    "type": "GET"
                }
            ],
            ...
        }
    }
```

To configure `apps-client` add a settings section like this to app config file:
```
    ...

    "settings": {
        "simple_example_conn": {
            "connection_str": "http://host1,http://host2"
        }
    }

```

The only required setting is `connection_str` but many other values can be configured:

```
    ...

    "settings": {
        "simple_example_conn": {
            "connection_str": "${HOPEIT_SIMPLE_EXAMPLE_HOSTS}",
            "circuit_breaker_open_failures": 10,
            "circuit_breaker_failure_reset_seconds": 90.0,
            "circuit_breaker_open_seconds": 60.0,
            "retries": 2,
            "retry_backoff_ms": 10,
            "ssl": true,
            "max_connections": 100,
            "max_connections_per_host": 0,
            "dns_cache_ttl": 10,
            "routes_override": {
                "__list-somethings": "simple-example/${HOPEIT_APPS_ROUTE_VERSION}/list-somethings"
            }
        }
    }
```

### Usage

Invoking target-app target-event from your application code:

```
    from hopeit.app.client import app_call

    ...

    def my_event(payload: ..., context: EventContext) -> ...:
        response = await app_call(
            "target-app-conn", event="target-event",
            datatype=ResposeDataType, payload=..., context=context
        )
    ...

```
