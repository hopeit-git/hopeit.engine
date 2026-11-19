# Basic-auth plugin

This is a development authentication example, not a production authentication
implementation; see [README.md](README.md). It is a Hopeit app exposing login,
refresh, logout, and token-decoding events.

## Usage

- Load [config/plugin-config.json](config/plugin-config.json) alongside the
  application and server configuration. Login, refresh, and logout use `OnApp`
  plug mode; decode is a standalone plugin endpoint.
- Follow the configured Basic, Refresh, and Bearer authentication methods and
  typed `AuthInfo` contracts in [the package](src/hopeit/basic_auth/__init__.py).
  Keep token material out of application logs.
- See [client-example/count_and_save.py](../../../apps/examples/client-example/src/client_example/count_and_save.py)
  for an app calling the authentication event before invoking another app.

## Development

Preserve token expiration, renewal, refresh-cookie, and logout behavior when
changing event handlers. Follow [the existing tests](test/unit/) and the root
guide's app logging conventions.

Run from the repository root:

```sh
make PLUGINFOLDER=plugins/auth/basic-auth lint-plugin
make PLUGINFOLDER=plugins/auth/basic-auth test-plugin
```
