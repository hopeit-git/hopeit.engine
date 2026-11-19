# Apps-client plugin

This package implements HTTP calls between Hopeit apps; it is used as a Python
dependency rather than an app exposing its own endpoints.

## Usage

- Configure `app_connections` with client `hopeit.apps_client.AppsClient` and
  declare each allowed target in the calling event's `connections` list. Configure
  connection settings, including `connection_str`, under the connection's key.
- Call `app_call` or `app_call_list` from `hopeit.app.client`, supplying the
  connection, target event, response datatype, payload, and current context.
  Use explicit result annotations. This framework API requires `EventContext`.
- Declare expected non-200 response types through the `responses` argument;
  follow [handle_responses.py](../../../apps/examples/client-example/src/client_example/handle_responses.py).
  Import shared contracts from model packages, not remote event handlers.
- Select the authentication strategy explicitly for the use case. Account for
  retries and circuit-breaker behavior when calling events with side effects.

## Development

Use [README.md](README.md), [the implementation](src/hopeit/apps_client/__init__.py),
and [tests](test/) for supported settings and lifecycle behavior. Test response
parsing, authentication/tracking propagation, connection cleanup, and retries
when changing those paths.

Run from the repository root:

```sh
make PLUGINFOLDER=plugins/clients/apps-client lint-plugin
make PLUGINFOLDER=plugins/clients/apps-client test-plugin
```
