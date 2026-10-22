# RFC: POLL event type

Status: Proposed

Related issue: [#36 — POLL event type](https://github.com/hopeit-git/hopeit.engine/issues/36)

## Purpose and decision

Allow an external worker to request the next item from a stream when it is ready
to process it. For example, a POST event publishes scraper jobs using
`write_stream`; several scrapers call a POLL endpoint to receive jobs from the
same consumer group.

Introduce `EventType.POLL`, exposed as an HTTP **GET** endpoint. Its incoming
payload comes exclusively from the event's `read_stream` configuration. Query
parameters are passed to hooks and steps as with GET events; a request body or
the existing GET `payload` query parameter cannot supply the event payload.

This RFC proposes a small implementation using the current HTTP execution path
and stream manager. It does not introduce another background consumer, broker
interface, or delivery protocol. This change contains the proposal only.

## Configuration and event implementation

Use the existing `ReadStreamDescriptor`, including its consumer group and queues:

```json
{
  "events": {
    "poll_job": {
      "type": "POLL",
      "read_stream": {
        "name": "scraper-jobs",
        "consumer_group": "scrapers"
      }
    }
  },
  "settings": {
    "poll_job": {
      "response_timeout": 5.0
    }
  }
}
```

The server must have its stream manager configured, as for STREAM events. Reject
a POLL event without `read_stream` or with an empty `queues` list during config
validation. Stream payload types use the same discovery as STREAM events:
annotated step arguments decorated with `@dataobject`, or `dataobjects` when
using a generic `DataObject` argument.

An implementation can use the existing event API and hook signatures. Assuming
`ScrapeJob` is the existing dataobject published to the stream:

```python
from hopeit.app.api import event_api
from hopeit.app.context import EventContext, PostprocessHook, PreprocessHook

from .data_model import ScrapeJob

__steps__ = ["prepare"]

__api__ = event_api(
    query_args=[("worker_id", str, "Worker requesting the next job")],
    responses={200: (ScrapeJob, "Next job")},
)
# event_api currently creates content schemas for every response. Add the
# bodyless response using its existing callable API specification mechanism.
_job_api = __api__


def __api__(module, app_config, event_name, plugin):
    spec = _job_api(module, app_config, event_name, plugin)
    spec["responses"]["204"] = {"description": "No job available"}
    return spec


async def __preprocess__(
    payload: ScrapeJob,
    context: EventContext,
    *,
    request: PreprocessHook,
    worker_id: str,
) -> ScrapeJob:
    return payload


async def prepare(
    payload: ScrapeJob, context: EventContext, *, worker_id: str
) -> ScrapeJob:
    return payload


async def __postprocess__(
    payload: ScrapeJob, context: EventContext, *, response: PostprocessHook
) -> ScrapeJob:
    response.set_header("X-Job-Id", payload.event_id())
    return payload
```

There is no `payload=` in `event_api`: the stream input type is not an HTTP
request schema. The response schema describes the output after steps and
`__postprocess__`, which may differ from the stream input type. A raw `__api__`
dictionary can also describe the 200 and bodyless 204 responses. No extension to
`event_api` is needed for the initial implementation.

## Request behavior

1. Resolve the route, settings, request tracking, query parameters, and
   authorization using the existing GET helpers. Reject a `payload` query
   parameter or nonempty request body with the existing 400 response before
   reading a message. Invalid authorization must also leave the stream unread.
2. Read at most one message from the configured stream and queues, as described
   below. No message means an empty HTTP **204** response. Do not run the event
   hooks or steps in this case.
3. Pass the decoded stream payload to `__preprocess__`, then execute the normal
   `__steps__` with its returned payload and the request query parameters.
   `PreprocessHook` exposes request headers; its `payload_raw` is `None` because
   the input was decoded by the stream manager. Preserve the existing preprocess
   status behavior: a status other than 200 skips steps and postprocessing.
4. Run `__postprocess__` and construct the response with the existing HTTP
   serializer and response hook. Preserve support for custom status, headers,
   cookies, and content types. A processed result of `None` follows normal HTTP
   event serialization; it is not an empty-stream signal.
5. If execution was not short-circuited and the constructed response is successful
   (2xx), call `ack_read_stream` for that message, then return the response.
   Failures, cancellation, preprocess short circuits, and non-2xx responses do
   not initiate an acknowledgment. An error returned as a stream-list element
   must be raised into the existing HTTP error path, rather than treated as an
   empty read or serialized as an event result.

Set `Cache-Control: no-store` on POLL responses, including 204. Register the GET
route with `allow_head=False`: aiohttp's automatic HEAD handler must not consume
a message. Retain existing route naming, custom routes, authentication, CORS,
and plugin routing conventions. POLL events have no `/start` or `/stop` routes
and are not started by `stream_startup_hook`.

Use the authenticated HTTP caller's context for hooks and steps. Do not replace
`auth_info` with the producer's credentials stored in the message. Keep HTTP
request/operation tracking IDs and merge the configured `stream.*` logging
fields from the message into that context, so the response remains associated
with the polling request and logs identify the consumed message.

## Reading one message

Add a small engine helper, provisionally `poll_stream(context)`, that returns
the selected stream name and `StreamEvent`, or `None`. Its job is just to read;
the HTTP path owns hooks, execution, response construction, and acknowledgment.

For each configured queue, in order:

- Resolve the stream name exactly as STREAM does: `AUTO` uses the base name;
  other queues use `<name>.<queue>`.
- Call the existing idempotent `ensure_consumer_group` for that stream/group.
- Call `stream_manager.read_stream` using the existing datatype discovery and
  tracking headers, `offset=">"`, **`batch_size=1`**, the configured
  `engine.read_stream_timeout`, and **`batch_interval=0`**.
- Return immediately on the first message. If that read is empty, try the next
  queue. After one empty pass through all queues, return `None`.

Do not use `settings.stream.batch_size` to decide how many jobs to consume: one
HTTP request returns at most one job, even when the normal batch size is 100.
There is no continuous retry on an empty stream and no sleep between read cycles.
Queue ordering matches existing STREAM behavior, including possible starvation
of later queues when earlier queues stay busy.

Require the existing `engine.read_stream_timeout` to be positive for POLL.
The Redis implementation passes this value to `XREADGROUP BLOCK`, where zero
would wait indefinitely. With multiple queues, an empty poll can take roughly
`len(queues) * read_stream_timeout` milliseconds, plus broker overhead.

Wrap the read, hooks, execution, response construction, and acknowledgment attempt
in one `settings.response_timeout` deadline. This also bounds consumer-group
setup and existing circuit-breaker backoff. Configure that deadline above the
expected empty-read duration to receive 204 normally. Reuse the current HTTP
timeout/error responses (currently 500); a deadline or broker failure is not an
empty-stream response. `settings.stream.timeout` remains the background STREAM
processing setting.

Requests can run concurrently without taking the background event's `_running`
lock. Workers using the same stream and consumer group compete for new messages;
different groups consume independently. A STREAM event on the same group also
competes, so it should use a different group if it must receive its own copy.

## Reuse and implementation scope

| Location | Proposed change |
| --- | --- |
| [`hopeit/app/config.py`](../../engine/src/hopeit/app/config.py) | Add `POLL` to `EventType`; document `read_stream` for STREAM and POLL; validate the required read configuration and positive read timeout for POLL. Reuse existing fields. |
| [`hopeit/server/engine.py`](../../engine/src/hopeit/server/engine.py) | Initialize the stream manager for POLL-only apps; add the single-message helper using `_find_stream_datatype_handlers` and the current stream manager. |
| [`hopeit/server/web.py`](../../engine/src/hopeit/server/web.py) | Register POLL as GET and add the small request handler around the existing request/context, authorization, `_request_execute`, response, and error helpers. Apply the overall deadline and acknowledgment ordering above. |
| [`hopeit/server/engine.py`](../../engine/src/hopeit/server/engine.py) and [`hopeit/server/web.py`](../../engine/src/hopeit/server/web.py) | Pass an optional `queue=StreamQueue.AUTO` argument through `_request_execute` and `AppEngine.execute` to `_execute_event`, so existing `write_stream` queue propagation receives the selected message's queue. Existing callers retain the default. |
| [`hopeit/server/api.py`](../../engine/src/hopeit/server/api.py) | Add `EventType.POLL: "get"` to `METHOD_MAPPING`. |
| [`hopeit/app/api.py`](../../engine/src/hopeit/app/api.py) | Use the HTTP method mapping in `api_from_config`; its current `type.value.lower()` would incorrectly look for a `poll` operation. |

The POLL handler can pass the stream payload to `_request_execute` and inspect
its `PreprocessHook.status` and returned response status before acknowledging.
The no-message branch constructs a bodyless response directly, using the normal
tracking headers. Keep these as local changes; no generalized request pipeline
or new configuration class is needed.

Do not call `AppEngine.read_stream(..., test_mode=True)` or adapt its continuous
loop into an HTTP handler. That path owns a per-event background lock, constructs
a context from the producer, passes no query arguments, and acknowledges before
HTTP hooks. Even its existing `max_events=1` option does not supply the required
HTTP lifecycle. Reusing `StreamManager` operations and normal event execution
avoids changing background STREAM behavior. No Redis plugin changes are needed.

Optional `write_stream` uses existing publication behavior; publication,
acknowledgment, and HTTP delivery are not atomic. Asynchronous step boundaries such as
`SHUFFLE` retain GET semantics: the response does not wait for downstream STREAM
stages. The job runner remains unchanged; POLL is initially an HTTP event.

## Acknowledgment and delivery limits

Acknowledgment means the backend handled the poll; it does **not** confirm that
the external scraper received the response or completed the job. There is a loss
window between acknowledgment and HTTP delivery. Postprocess hooks that start
sending a streaming response have the same limitation, since delivery can begin
before acknowledgment. A failed acknowledgment can also leave a successfully
returned job pending.

In particular, `StreamCircuitBreaker.ack_read_stream` currently records and
suppresses `StreamOSError`. Reuse that behavior in this minimal implementation;
do not claim that HTTP 200 proves acknowledgment succeeded. Exceptions that do
propagate follow the existing HTTP error handling.

Failures after a read leave messages pending, including a preprocess rejection.
Reading with `offset=">"` does not automatically reclaim them on the next poll.
This RFC adds no pending-message recovery, leases, completion endpoint, or
exactly-once guarantee. Applications requiring confirmation of external work
completion need a separate protocol. Because GET consumes work, clients should
also avoid prefetching or automatically retrying an ambiguous failed request.

## Validation for the implementation

Extend the existing config, engine, web, and OpenAPI tests using the stream
mocks; keep real Redis integration checks focused on broker behavior:

- Config parsing accepts POLL, rejects missing read configuration and invalid
  read timeouts, and initializes a stream manager in an app containing only POLL.
- One GET reads at most one message even with the default batch size; the module
  receives its typed payload, query arguments, and HTTP caller context. Assert
  preprocess → steps → postprocess → response construction → acknowledgment.
- Empty reads return a bodyless 204, skip hooks/steps/ack, and stop after one pass.
  Cover queue suffixes, ordering, and stopping immediately after the first item.
- Auth rejection, a body, `payload` query input, and HEAD never read the stream.
  Successful and empty responses include tracking and `Cache-Control: no-store`.
- Preprocess short circuits, processing/postprocessing/serialization failures,
  non-2xx responses, decoding errors, and cancellation do not initiate an ack.
  Deadline/backoff failures use the existing error response, rather than 204.
  Characterize the circuit breaker's suppressed ack failure explicitly.
- OpenAPI exposes `get`, query parameters, typed 200 and bodyless 204, and no
  request body. Cover `api_from_config` and normal/custom/plugin routes.
- Concurrent requests can read distinct jobs without an event-lock failure;
  verify same-group distribution with Redis. Confirm POLL is not auto-started,
  `write_stream` preserves queue routing, and existing GET/POST/STREAM tests pass.
