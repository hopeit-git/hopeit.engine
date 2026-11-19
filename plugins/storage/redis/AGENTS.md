# Redis storage plugin

This package supplies asynchronous Redis key/value persistence for dataobjects.
It is a Python dependency, separate from the Redis Streams transport plugin.

## Usage

- Initialize `RedisStorage().connect(address=..., username=..., password=...)`
  through the app's resource initialization using configured connection values.
- Await `store(key, value)` and `get(key, datatype=Type)`. Values are serialized
  through `Payload`; a missing key returns `None`.
- `store` forwards Redis SET options such as `ex` for expiry and `nx` for
  create-only writes. Choose these intentionally for the app's persistence needs.
  `delete` and `list_objects` operate on Redis keys, not stream consumer groups.

## Development

Use [the implementation](src/hopeit/redis_storage/__init__.py) and [tests](test/)
to check serialization, missing values, and forwarded SET options. Keep its
connection and storage behavior independent of Redis Streams configuration.

Run from the repository root:

```sh
make PLUGINFOLDER=plugins/storage/redis lint-plugin
make PLUGINFOLDER=plugins/storage/redis test-plugin
```
