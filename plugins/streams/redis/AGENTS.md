# Redis Streams plugin

This package implements `RedisStreamManager`. Its Hopeit app supplies a SETUP
event for Redis authentication and blocking connection-pool configuration.

## Usage

- Configure the server's stream manager as `hopeit.redis_streams.RedisStreamManager`
  and set its connection string; see [dev-local.json](../../../engine/config/dev-local.json).
  Include [config/plugin-config.json](config/plugin-config.json) when configuring
  the custom connection factory through `setup_redis_pool`.
- Configure producer/consumer names, named queues, and consumer groups in the app
  events. Follow [the streaming example](../../../apps/examples/simple-example/config/app-config.json)
  and the root guide's routing and SHUFFLE guidance. Start background consumers
  with `--start-streams`.
- Treat broker read timeout, pool/socket timeouts, and event processing timeout as
  separate settings. Check the broker and routing before increasing them.

## Current limits and development

The reader uses new-message reads and does not automatically reclaim pending
messages. The engine stream circuit breaker logs and suppresses acknowledgment
`StreamOSError`s. Do not describe transparent recovery or exactly-once work
completion as supported, or prescribe app-level recovery machinery as a standard
usage requirement. Changes to recovery belong in framework/plugin work.

Check [the transport](src/hopeit/redis_streams/__init__.py),
[pool setup](src/hopeit/redis_streams/setup_redis_pool.py), and [tests](test/).
Verify read/write serialization, acknowledgment, and pool lifecycle when changing
these paths.

Run from the repository root:

```sh
make PLUGINFOLDER=plugins/streams/redis lint-plugin
make PLUGINFOLDER=plugins/streams/redis test-plugin
```
