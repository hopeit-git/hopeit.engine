# Working on hopeit.engine

These instructions apply throughout the repository. Before editing a directory,
read any additional `AGENTS.md` files along its path and follow their more specific
guidance. Keep instructions, comments, and documentation in English.

The development section covers work on this repository. The app-building section
covers using hopeit.engine; follow existing internal conventions when changing
the engine itself. Read a plugin's linked guide before using or editing it.

## Repository and development

hopeit.engine runs typed event pipelines triggered by HTTP requests, streams,
services, or startup. Apps consist of configuration plus importable Python modules;
multiple apps can run in one server process.

| Location | Purpose |
| --- | --- |
| `engine/src/hopeit/` | Engine, app APIs, dataobjects, CLI, and testing utilities |
| `engine/test/unit/`, `engine/test/integration/` | Engine tests |
| `plugins/` | Hopeit apps providing endpoints or streams, and packages used as Python dependencies |
| `apps/examples/`, `apps/tutorials/` | Working examples and tutorial apps |
| `docs/source/`, `docs/rfcs/` | Documentation and design proposals |

Run commands from the repository root. Reuse the existing development environment;
use `make dev` when setting up a development checkout. Use the latest supported
Python for development, examples, and guidance; the Makefile currently defaults
to Python 3.14. Keep changes compatible with the Python versions declared in the
project and CI.
Use `uv run --no-sync` for commands in the prepared environment.

Prefer small changes that reuse existing engine, plugin, and app functionality.
Treat RFCs as proposals: check the implementation before claiming a feature exists.
Preserve unrelated working-tree changes and keep them out of commits.

### Validation and review

Use the Makefile targets for the affected component:

| Scope | Commands |
| --- | --- |
| Engine | `make lint-engine`, `make test-engine` |
| One plugin | `make PLUGINFOLDER=plugins/data/dataframes lint-plugin`, `make PLUGINFOLDER=plugins/data/dataframes test-plugin` |
| One example app | `make APPFOLDER=apps/examples/simple-example lint-app`, `make APPFOLDER=apps/examples/simple-example test-app` |
| Repository-wide changes | `make lint`, `make test` |

For focused investigation, run a specific test through `uv run --no-sync pytest`
with the component's `PYTHONPATH` from its Make target. Engine and example targets
enforce 90% coverage; plugin targets enforce 80%.

- Use `hopeit.testing.apps.config`, `create_test_context`, and `execute_event`
  for event tests. `execute_event` ignores stream writes; verify routing and
  producer/consumer handoffs separately when they change.
- Test meaningful boundary behavior: validation, JSON round trips, defaults,
  SDK conversions, saved-data loading, and payload isolation. Assert behavior
  rather than pinning production tuning values.
- Regenerate affected OpenAPI artifacts when contracts change;
  `make update-examples-api` handles bundled example specs. Use `make schemas`
  when app/server configuration schemas change. Check affected consumers and
  imports as well as the generated output.
- For documentation-only changes, check links, examples, and
  `git diff --check`; a full runtime suite is unnecessary. Report the validation
  actually performed and any remaining limitations.
- When addressing PR review comments, commit and push changes only at the user's
  request. After those changes are committed and pushed, reply to each addressed
  review comment, briefly explaining the change and linking the relevant commit.
  Include validation or remaining limitations where relevant.

## Good practices when building Hopeit apps

### Dataobjects and serialization

Use Hopeit's Pydantic-compatible helpers for public payloads and configuration:

```python
from datetime import datetime

from hopeit.dataobjects import dataclass, dataobject, field, fields
from hopeit.dataobjects.payload import Payload


@dataobject
@dataclass
class JobOptions:
    retries: int = field(default=0, ge=0)


@dataobject
@dataclass
class Job:
    job_id: str
    created_dt: datetime
    options: JobOptions = field(default_factory=JobOptions)
```

- Keep `@dataobject` above `@dataclass`. Standard-library `dataclasses.dataclass`
  is incompatible with this decorator; it remains appropriate for internal types
  that are not Hopeit dataobjects.
- Prefer declared, typed dataobjects for structured fields and nested settings
  instead of dictionaries. Use plain `@dataobject` for the usual case.
- Dataobjects use Pydantic dataclasses, with BaseModel-style validation and
  serialization exposed through `Payload`'s Pydantic `RootModel` wrapper. Use
  Pydantic functionality, including constraints, validators, configuration, and
  schema generation, when modeling and validating data.
- Import `field` and `fields` from `hopeit.dataobjects` too. `fields(Type)` returns
  a name-keyed mapping of Pydantic `FieldInfo`; iterate with `.items()` or `.keys()`.
- Use `field(default_factory=...)` for mutable defaults and nested configuration.
- Use `Payload.to_json` / `Payload.from_json` for JSON and `Payload.to_obj` /
  `Payload.from_obj` for mappings. Use `mode="json"` with `to_obj` when the output
  must contain JSON-compatible values.
- When deriving a validated payload, prefer reconstruction through `Payload`
  rather than `dataclasses.replace` or copying an object and mutating its fields:

  ```python
  from typing import Any, cast

  values: dict[str, Any] = cast(dict[str, Any], Payload.to_obj(original))
  derived: Job = Payload.from_obj({**values, "job_id": "another-job"}, Job)
  ```

  The cast describes this known dataobject mapping to the type checker; it adds
  no runtime assertion. Reconstruction is for deriving and validating a new
  payload, not defensive copying between steps.
- The engine serializes/deserializes mutable payloads with pickle before normal
  step calls, isolating their nested data. Do not add `deepcopy` or defensive
  copies around ordinary step handoffs; the engine handles that. Advanced
  `@dataobject(unsafe=True)` opts out of copying; frozen dataclasses also bypass
  it. Review mutation when opting out or reusing objects in generators/`Spawn`.
- Advanced stream identity options are `@dataobject(event_id="job_id",
  event_ts="created_dt")`. Without them, `event_id()` generates a UUID on every
  call and `event_ts()` returns `None`.

Put shared request/response types and stream contracts in a shared model module
or package. Import those types directly rather than through event handlers, which
can pull backend dependencies into gateways and OpenAPI generation. Keep internal
state local when it is not exchanged. Represent external SDK configuration with a
serializable application-owned type and convert it in an integration helper.
Declare direct dependencies for imported packages. Preserve serialized names and
enum values when saved payloads still require them, even if new execution no
longer accepts those values.

### Events, APIs, and logging

- Declare ordered steps in `__steps__` and annotate payloads and return types.
  Dispatch finds the next compatible step; a mismatched annotation can skip work.
  Use `EventContext` for settings, authorization, and tracking information.
- Declare HTTP contracts with `__api__ = event_api(...)`. Use `__preprocess__`
  and `__postprocess__` hooks for request/response concerns and `PostprocessHook`
  for status and headers. Follow the examples under `apps/examples/`.
- Read typed settings with an explicit result annotation for mypy:
  `settings: SettingsType = context.settings(key="settings_key", datatype=SettingsType)`.
  Reuse `SETUP` events or `__init_event__` initialization patterns for resources.
- Keep event steps responsible for orchestration. Reusable computation belongs
  in helper modules; a library using Hopeit dataobjects need not be a Hopeit app.
- In app events, use `app_logger()` or `app_extra_logger()` from
  `hopeit.app.logger`, passing `context` to log calls. A message such as
  `logger.info(context, "Processing job")` need not log the payload. Use the
  `extra` helper only for relevant, deliberately selected metadata.
- Log from app events; return diagnostics or counts from inner helpers. Keep
  `EventContext` in the event layer when possible, passing helpers the specific
  settings or data they need. Framework APIs that require context are an exception.
- Log actual work and useful identifiers. Avoid completion messages for skipped
  stages and dumping payloads or detailed business results into structured logs.

### Streams and asynchronous work

- Verify the whole route: producer `write_stream.name` and queues → consumer
  `read_stream.name`, queues, and `consumer_group` → next producer.
- `AUTO` uses the base stream name; named queues add a suffix. Consumers must
  explicitly list the queues they need. `PROPAGATE` preserves an incoming named
  queue; `DROP` uses outgoing configuration and is the default strategy.
- Consumers sharing a group compete for messages. Use separate groups when
  independent consumers each need a copy.
- `Spawn[T]` yields multiple payloads from an async generator.
- In a GET/POST event, the HTTP result comes from the steps before the first
  `SHUFFLE`; `__postprocess__` can modify that response. Steps after `SHUFFLE`
  execute asynchronously in the background, with streams carrying their payloads.
  The engine automatically creates the producer and stream consumer stages from
  the same event module. Start streams to run the background stages.
- Distinguish broker read timeout, socket timeout, stream processing timeout,
  and HTTP response timeout. Check routing, broker health, payload size, and
  event-loop blocking separately before assigning a cause or changing a timeout.

## Plugins

Plugins are usually Hopeit apps providing endpoints, stream handlers, or setup
events; some provide only Python library functionality. Read their own guidance:

| Plugin | Guide |
| --- | --- |
| Development authentication | [basic-auth](plugins/auth/basic-auth/AGENTS.md) |
| Calls between apps | [apps-client](plugins/clients/apps-client/AGENTS.md) |
| Typed dataframes and datasets | [dataframes](plugins/data/dataframes/AGENTS.md) |
| App and event visualization | [apps-visualizer](plugins/ops/apps-visualizer/AGENTS.md) |
| Runtime and cluster configuration | [config-manager](plugins/ops/config-manager/AGENTS.md) |
| Log collection service | [log-streamer](plugins/ops/log-streamer/AGENTS.md) |
| Filesystem persistence | [fs-storage](plugins/storage/fs/AGENTS.md) |
| Redis key/value persistence | [redis-storage](plugins/storage/redis/AGENTS.md) |
| Redis stream transport | [redis-streams](plugins/streams/redis/AGENTS.md) |

Use [README.md](README.md), [tutorials](docs/source/tutorials/), and existing
examples for usage. Check [dataobjects](engine/src/hopeit/dataobjects/),
[event configuration](engine/src/hopeit/app/config.py), and
[step execution](engine/src/hopeit/server/steps.py) for exact behavior.
