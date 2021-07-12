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
