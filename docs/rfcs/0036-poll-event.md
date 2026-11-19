# RFC: POLL event type

Status: Proposed

Related issue: [#36 — POLL event type](https://github.com/hopeit-git/hopeit.engine/issues/36)

Discussion: [PR #230](https://github.com/hopeit-git/hopeit.engine/pull/230)

## Decision

Add `EventType.POLL`: an HTTP **POST** endpoint that reads at most one stream
message, runs the event's hooks and steps, and returns the result. An empty read
returns **204 No Content**. External workers call it when ready for more work;
workers sharing a consumer group compete for messages.

POST fits because reading and acknowledging a message changes consumer-group
state. The payload comes from `read_stream`; query arguments work as for POST
events. Requests have no body. Keep POLL distinct from POST so the source of the
payload is unambiguous.

Acknowledgment happens in the backend, before returning the response. It does
**not** confirm receipt or completion of work by the external worker. Reliable
external job completion requires a separate protocol.

## Configuration and example

Reuse `ReadStreamDescriptor` and the existing timeout settings:

```json
{
  "engine": {
    "read_stream_timeout": 1000
  },
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
      "response_timeout": 10.0
    }
  }
}
```

Require a configured stream manager, `read_stream`, nonempty `queues` (default
`["AUTO"]`), and positive timeouts. Discover stream payload types from annotated
steps or the explicit `dataobjects` list, as for STREAM events.

Assuming `ScrapeJob` is the dataobject published to the stream:

```python
from hopeit.app.api import event_api
from hopeit.app.context import EventContext

from .data_model import ScrapeJob

__steps__ = ["prepare"]
__api__ = event_api(
    query_args=[("worker_id", str, "Worker requesting the next job")],
    responses={200: (ScrapeJob, "Next job")},
)


async def prepare(
    payload: ScrapeJob, context: EventContext, *, worker_id: str
) -> ScrapeJob:
    return payload
```

Normal `__preprocess__` and `__postprocess__` hooks remain available. Omit
`payload=` from `event_api`: the input is not an HTTP body. POLL OpenAPI generation
adds bodyless 204 automatically, avoiding a custom `__api__` wrapper per event.
The declared 200 schema describes the output after processing.

## Request lifecycle

1. Create the normal HTTP context, extract query arguments, and authorize the
   caller. Reject a nonempty request body with 400 before reading the stream.
2. Read one message. If all queues are empty, return bodyless 204 with normal
   tracking headers; skip hooks, steps, and acknowledgment.
3. Pass the decoded payload through preprocess → steps → postprocess → response
   construction using existing HTTP helpers. `PreprocessHook.payload_raw` is
   `None`. Preserve normal hook behavior, including preprocess short circuits
   and custom status, headers, cookies, and content types.
4. If preprocess did not short-circuit and the constructed response is 2xx,
   attempt acknowledgment, then return the response. Errors, cancellation,
   preprocess short circuits, and non-2xx responses do not initiate an ack.

Only an empty read signals "no work"; a processed result of `None` uses normal
HTTP serialization. Raise exceptions returned inside a stream batch into the
existing HTTP error path, never treat them as an empty read.

Keep the HTTP caller's authorization and tracking IDs; include configured
`stream.*` logging fields to identify the message. Producer credentials must not
replace the caller's identity. Retain normal routing, plugin, and CORS behavior.
Register only POST; POLL has no background startup or management routes.

## Reading and timeouts

Add one engine helper returning `(stream_name, StreamEvent)` or `None`. Visit
queues in configured order, resolving `AUTO` to the base stream name and other
queues to `<name>.<queue>`. For each queue, ensure the consumer group and read with
`offset=">"`, **`batch_size=1`**, **`batch_interval=0`**, and the configured
`engine.read_stream_timeout`. Return the first message, or stop after one empty
pass. Raise any read error immediately.

Each broker read may block for its timeout; there is no repeated polling within
one request. `settings.stream.batch_size` does not affect the read count. Busy
earlier queues can starve later ones, as with STREAM. Concurrent requests need
no background event lock. A STREAM consumer sharing the group competes with
POLL; use separate groups when each consumer needs its own copy.

Use one `settings.response_timeout` deadline covering group setup, reads, hooks,
steps, serialization, and the acknowledgment attempt:

```text
empty-read budget (seconds) ≈ len(queues) × engine.read_stream_timeout / 1000
response_timeout > empty-read budget + processing/ack budget + overhead margin
```

Reject configurations where `response_timeout` does not exceed the empty-read
budget. This is a minimum check; operators must also budget for processing,
broker latency, and circuit-breaker backoff. The example allows roughly one
second for an empty read and nine seconds for other work. A late-arriving message
must still fit the remaining budget; reading does not reset the deadline.

Require `read_stream_timeout > 0`: Redis interprets zero as an indefinite wait.
`settings.stream.timeout` remains the background STREAM processing setting.
A deadline or broker failure uses the existing HTTP error response (currently
500), never 204. The client timeout should exceed `response_timeout` with a
network margin.

## Delivery limits and clients

| Situation | Outcome |
| --- | --- |
| Backend fails after reading, before acknowledgment | Message remains pending. Later polls read new messages, not pending ones. |
| Backend acknowledges, but response is lost or worker crashes | The group will not redeliver the job; external work can be lost. |
| Acknowledgment raises `StreamOSError` | The circuit breaker logs and suppresses it; the client can receive 200 while the message remains pending. |

The current Redis plugin has no automatic pending-message reclaim (`XAUTOCLAIM`
or equivalent). Shared recovery belongs in a separate change for STREAM and
POLL. This RFC provides neither at-least-once completion nor exactly-once
delivery. Future recovery can redeliver pending messages, so workers should
handle duplicate job IDs.

Retain existing acknowledgment error logging; monitor those errors and pending
message counts operationally. HTTP success does not prove acknowledgment
succeeded. No new response flags or metrics subsystem are required here.
Optional `write_stream` publication, acknowledgment, and HTTP delivery are not
atomic; `SHUFFLE` does not wait for downstream stages. Streaming responses can
begin delivery during postprocess, before acknowledgment.

Clients should process a job before polling again. On 204, wait using a
configurable interval or capped backoff with jitter; reset backoff when work
arrives. Do not automatically replay an ambiguous failed POST: it may have
consumed a job, and another call can consume a different one. Retrying POLL
cannot recover that job.

`hopeit.apps_client` support is a focused follow-up. Its POST path currently
serializes a body even for `payload=None`, its parser expects response content,
and its retry loop can replay failed calls. POLL support must send bodyless POST,
map 204 to an empty result, and disable automatic retries for these calls. It
needs no new HTTP method. Until then, use an HTTP client following this contract.

## Implementation and acceptance

Keep changes local to existing components:

- **Config:** add POLL and validate its read configuration and timeout budget.
- **Engine:** initialize streams in POLL-only apps and add the single-message
  helper using existing datatype discovery and stream-manager operations.
- **Web:** add the POST handler around normal HTTP helpers, with the overall
  deadline and ack ordering above. Pass the message's queue through
  `_request_execute` and `AppEngine.execute` to `_execute_event` using an optional
  argument defaulting to `StreamQueue.AUTO`, preserving `write_stream` routing.
- **OpenAPI:** map POLL to `post`, add bodyless 204, and use the method mapping in
  `api_from_config` instead of `type.value.lower()`.

Do not reuse the background `AppEngine.read_stream` loop: it owns a lock, uses
producer context, and does not implement the HTTP hook lifecycle. No new broker
interface, configuration class, or Redis plugin behavior is needed.

Verify with existing config, engine, web, and OpenAPI tests:

- Valid/invalid config, POLL-only initialization, timeout units/budget; POST
  routing, typed 200, bodyless 204, and no request body schema.
- One message per request, queue order/suffixes and output routing; typed input,
  query arguments, caller identity, and tracking through hooks.
- Empty reads skip processing/ack; auth rejection and invalid bodies never read;
  GET/HEAD cannot consume. Include normal, custom, and plugin routes.
- Response construction precedes ack; short circuits, non-2xx, decoding errors,
  processing/serialization failures, and cancellation do not initiate ack. Cover
  deadlines during reads and after late arrivals, plus logged, suppressed ack
  failures.
- Concurrent requests consume distinct messages in a Redis group; POLL is not
  auto-started; existing GET/POST/STREAM behavior remains unchanged.
