# Log-streamer plugin

This Hopeit app runs a log-reader SERVICE, parses engine lifecycle records into
typed log batches, and publishes them to `hopeit.log-streamer.logs` for consumers
such as apps-visualizer.

## Usage

- Adapt [config/plugin-config.json](config/plugin-config.json) to the local log
  and checkpoint paths. Follow [README.md](README.md) to run a separate server
  on each monitored node; `make run-log-streamer` is the repository shortcut.
- Start streams/services with `--start-streams`. Match output stream configuration
  with the visualizer's `event-stats.collect` input.
- Use the configured batch size, wait interval, file inactivity timeout, and
  checkpoint expiry rather than introducing a second polling mechanism.

## Development

Preserve lifecycle parsing for `START`, `DONE`, `FAILED`, and `IGNORED`, plus file
watcher cleanup and checkpoint behavior. See [log_reader.py](src/hopeit/log_streamer/log_reader.py)
and [integration tests](test/integration/). Test batching and file-handler changes
against existing fixtures; keep watcher failures observable through app events.

Run from the repository root:

```sh
make PLUGINFOLDER=plugins/ops/log-streamer lint-plugin
make PLUGINFOLDER=plugins/ops/log-streamer test-plugin
```
