# Working on hopeit.engine

These instructions apply throughout the repository. Before editing a directory,
read any additional `AGENTS.md` files along its path and follow their more specific
guidance. Keep instructions, comments, and documentation in English.

## Repository and development

hopeit.engine runs typed event pipelines triggered by HTTP requests, streams,
services, or startup. Apps consist of configuration plus importable Python modules;
multiple apps can run in one server process.

| Location | Purpose |
| --- | --- |
| `engine/src/hopeit/` | Engine, app APIs, dataobjects, CLI, and testing utilities |
| `engine/test/unit/`, `engine/test/integration/` | Engine tests |
| `plugins/` | Separately packaged auth, client, dataframes, operations, storage, and stream integrations |
| `apps/examples/`, `apps/tutorials/` | Working examples and tutorial apps |
| `docs/source/`, `docs/rfcs/` | Documentation and design proposals |

Run commands from the repository root. Reuse the existing development environment;
use `make dev` when setting up a development checkout. The Makefile defaults to
Python 3.14; `make PYTHONVERSION=3.11 dev` selects another supported interpreter.
Keep changes compatible with the Python versions declared in the project and CI.
Use `uv run --no-sync` for commands in the prepared environment.

Prefer small changes that reuse existing engine, plugin, and app functionality.
Treat RFCs as proposals: check the implementation before claiming a feature exists.
Preserve unrelated working-tree changes and keep them out of commits.

## Dataobjects and serialization

Use Hopeit's Pydantic-compatible helpers for public payloads and configuration:

```python
from datetime import datetime

from hopeit.dataobjects import dataclass, dataobject, field, fields
from hopeit.dataobjects.payload import Payload


@dataobject(event_id="job_id", event_ts="created_dt")
@dataclass
class Job:
    job_id: str
    created_dt: datetime
    options: dict[str, str] = field(default_factory=dict)
```

- Keep `@dataobject` above `@dataclass`. Standard-library `dataclasses.dataclass`
  is incompatible with this decorator; it remains appropriate for internal types
  that are not Hopeit dataobjects.
- Import `field` and `fields` from `hopeit.dataobjects` too. `fields(Type)` returns
  a name-keyed mapping of Pydantic `FieldInfo`; iterate with `.items()` or `.keys()`.
- Use `field(default_factory=...)` for mutable defaults and nested configuration.
- Use `Payload.to_json` / `Payload.from_json` for JSON and `Payload.to_obj` /
  `Payload.from_obj` for mappings. Use `mode="json"` with `to_obj` when the output
  must contain JSON-compatible values.
- When deriving a validated payload, prefer reconstruction through `Payload`
  rather than `dataclasses.replace` or copying an object and mutating its fields:

  ```python
  values = Payload.to_obj(original)
  assert isinstance(values, dict)
  derived = Payload.from_obj({**values, "job_id": "another-job"}, Job)
  ```

  Test nested-data independence where derived objects can be mutated separately.
  Serializing an already-mutated object is not a substitute for validation.
- Configure `event_id` and `event_ts` when stream messages need stable identity.
  Without expressions, `event_id()` generates a UUID on every call and
  `event_ts()` returns `None`.
- Mutable payloads are normally copied between steps. `unsafe=True` opts out;
  frozen dataclasses also bypass copying. Review mutation carefully when using
  generators or `Spawn`, especially if an object is reused after a yield.

Put shared request/response types and stream contracts in a shared model module
or package. Import those types directly rather than through event handlers, which
can pull backend dependencies into gateways and OpenAPI generation. Keep internal
state local when it is not exchanged. Represent external SDK configuration with a
serializable application-owned type and convert it in an integration helper.
Declare direct dependencies for imported packages. Preserve serialized names and
enum values when saved payloads still require them, even if new execution no
longer accepts those values.

## Events, APIs, and logging

- Declare ordered steps in `__steps__` and annotate payloads and return types.
  Dispatch finds the next compatible step; a mismatched annotation can skip work.
  Use `EventContext` for settings, authorization, and tracking information.
- Declare HTTP contracts with `__api__ = event_api(...)`. Use `__preprocess__`
  and `__postprocess__` hooks for request/response concerns and `PostprocessHook`
  for status and headers. Follow the examples under `apps/examples/`.
- Read typed settings through
  `context.settings(key="settings_key", datatype=SettingsType)`. Reuse existing
  `SETUP` events or `__init_event__` initialization patterns for resources.
- Keep event steps responsible for orchestration. Reusable computation belongs
  in helper modules; a library using Hopeit dataobjects need not be a Hopeit app.
- In app events, use `app_logger()` or `app_extra_logger()` from
  `hopeit.app.logger`, passing `context` to log calls. With `logger, extra =
  app_extra_logger()`, use `logger.info(context, "Processing job",
  extra=extra(job_id=payload.job_id))`.
- Put app progress logging in the event steps. Return diagnostics or counts from
  inner calculation helpers instead of logging there. Keep the engine's existing
  internal logging conventions when changing engine internals.
- Log actual work and useful identifiers. Avoid completion messages for skipped
  stages and dumping payloads or detailed business results into structured logs.

## Streams and asynchronous work

- Verify the whole route: producer `write_stream.name` and queues → consumer
  `read_stream.name`, queues, and `consumer_group` → next producer.
- `AUTO` uses the base stream name; named queues add a suffix. Consumers must
  explicitly list the queues they need. `PROPAGATE` preserves an incoming named
  queue; `DROP` uses outgoing configuration and is the default strategy.
- Consumers sharing a group compete for messages. Use separate groups when
  independent consumers each need a copy.
- `Spawn[T]` yields multiple payloads from an async generator. `SHUFFLE` splits
  event stages across a stream boundary; publishing does not await downstream
  completion. Use a request/result continuation when later work depends on it.
- Persist orchestration state before dispatch when recovery requires it. Carry
  correlation IDs through messages and validate results/cache identity against
  the request and relevant configuration. Handle replay at the app boundary;
  stream transport alone does not guarantee exactly-once work completion.
- Distinguish broker read timeout, socket timeout, stream processing timeout,
  and HTTP response timeout. Check routing, broker health, payload size, and
  event-loop blocking separately before assigning a cause or changing a timeout.
- Check the selected stream plugin's recovery and acknowledgment behavior. The
  current Redis reader does not automatically reclaim pending messages, and the
  stream circuit breaker can log and suppress acknowledgment `StreamOSError`s.

## Dataframes and storage

- Use `@dataframe` above Hopeit's `@dataclass` for typed Polars containers.
  `DataFrames.from_df(Type, df)` constructs them; `DataFrames.df(value)` accesses
  Polars; `DataFrames.schema(Type)` exposes the schema.
- Normal construction selects declared columns, applies the schema, supplies
  declared defaults, and checks non-nullable fields. A missing column declared
  as `score: float | None = None` becomes a typed all-null column. Nullable typing
  alone does not specify a default; column presence does not prove a feature is
  enabled or populated.
- Use `Dataset.save` / `Dataset.load` for persisted dataframe references, with
  the plugin's registry/storage setup loaded. Consumers need compatible type
  registration and access to that storage. Send references instead of large
  matrices where the pipeline uses datasets.
- Keep timestamps and storage partitioning distinct from local business dates.
  Preserve timezone-aware instants across conversions. Verify unique storage
  keys for separate output blocks so partitioned writes cannot overwrite data.

## Validation and review

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
- Test meaningful boundary behavior: JSON round trips, defaults/nulls, nested
  independence, SDK/dataframe conversion, saved-data loading, and replay.
  Assert behavior rather than pinning production tuning values.
- Regenerate affected OpenAPI artifacts when contracts change;
  `make update-examples-api` handles bundled example specs. Use `make schemas`
  when app/server configuration schemas change. Check affected consumers and
  imports as well as the generated output.
- For documentation-only changes, check links, examples, and
  `git diff --check`; a full runtime suite is unnecessary. Report the validation
  actually performed and any remaining limitations.

Use [README.md](README.md), [tutorials](docs/source/tutorials/), and existing
examples for usage. Check [dataobjects](engine/src/hopeit/dataobjects/),
[event configuration](engine/src/hopeit/app/config.py),
[step execution](engine/src/hopeit/server/steps.py), and
[dataframes](plugins/data/dataframes/src/hopeit/dataframes/) for exact behavior.
