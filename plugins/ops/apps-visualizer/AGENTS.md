# Apps-visualizer plugin

This Hopeit app provides the operations UI and endpoints for event/stream graphs
and live activity. It consumes configuration from config-manager and log batches
from log-streamer.

## Usage

- Run config-manager on monitored servers. Load this plugin's
  [configuration](config/plugin-config.json) in the visualization server and set
  `HOPEIT_APPS_VISUALIZER_HOSTS` to monitored URLs, optionally including `in-process`.
- The UI route is `/ops/apps-visualizer`. Follow [README.md](README.md) for startup
  commands and `make run-apps-visualizer` in the root Makefile.
- Live activity requires log-streamer and the `event-stats.collect` stream consumer
  reading `hopeit.log-streamer.logs`; start streams to enable collection.

## Development

Preserve graph expansion for SHUFFLE-generated event stages and stream/queue
routing. Check [graph tests and fixtures](test/integration/) when changing graph
construction. Follow the existing collector steps and templates rather than
adding a separate frontend stack. Verify static and live views for UI changes.

Run from the repository root:

```sh
make PLUGINFOLDER=plugins/ops/apps-visualizer lint-plugin
make PLUGINFOLDER=plugins/ops/apps-visualizer test-plugin
```

Use `make update-examples-api` when this plugin's API contract changes.
