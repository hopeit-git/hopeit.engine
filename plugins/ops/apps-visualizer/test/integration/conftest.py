import asyncio
import json
import os
from pathlib import Path
from datetime import datetime, timezone
import socket

import pytest

from hopeit.server.version import APPS_API_VERSION, APPS_ROUTE_VERSION
from hopeit.server import config as server_config
from hopeit.testing.apps import config, execute_event

from hopeit.log_streamer import LogRawBatch, LogBatch

from . import mock_getenv

_mock_lock = asyncio.Lock()


@pytest.fixture
def plugin_config(monkeypatch):
    monkeypatch.setattr(server_config.os, "getenv", mock_getenv)
    return config("plugins/ops/apps-visualizer/config/plugin-config.json")


@pytest.fixture
def events_graph_data_standard():
    with open(
        Path(os.path.dirname(os.path.realpath(__file__))) / "events_graph_data_standard.json"
    ) as f:
        json_str = f.read().replace("${APPS_ROUTE_VERSION}", APPS_ROUTE_VERSION)
        return json.loads(json_str)


@pytest.fixture
def events_graph_data_expanded():
    with open(
        Path(os.path.dirname(os.path.realpath(__file__))) / "events_graph_data_expanded.json"
    ) as f:
        json_str = f.read().replace("${APPS_ROUTE_VERSION}", APPS_ROUTE_VERSION)
        return json.loads(json_str)


@pytest.fixture
def effective_events():
    with open(Path(os.path.dirname(os.path.realpath(__file__))) / "effective_events.json") as f:
        json_str = f.read().replace("${APPS_ROUTE_VERSION}", APPS_ROUTE_VERSION)
        return json.loads(json_str)


async def _process_log_entries(raw: LogRawBatch) -> LogBatch:
    plugin_config = config("plugins/ops/log-streamer/config/plugin-config.json")
    return await execute_event(plugin_config, "log_reader", payload=raw)  # type: ignore


@pytest.fixture
def mock_lock():
    return _mock_lock


@pytest.fixture
async def log_entries() -> LogBatch:
    raw = LogRawBatch(
        data=[
            f"2021-06-02 18:01:44,290 | INFO | simple-example {APPS_API_VERSION} query_something host 17031 | START | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test",  # noqa: E501
            f"2021-06-02 18:01:44,303 | INFO | simple-example {APPS_API_VERSION} query_something host 17031 | DONE | response.status=404 | metrics.duration=13.057 | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test",  # noqa: E501
            f"2021-06-02 18:01:44,290 | INFO | simple-example {APPS_API_VERSION} save_something host 17031 | START | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test",  # noqa: E501
            f"2021-06-02 18:01:44,290 | INFO | simple-example {APPS_API_VERSION} service.something_generator host 17031 | START | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test |  stream.name=simple_example.{APPS_ROUTE_VERSION}.streams.something_event | stream.queue=AUTO",  # noqa: E501
            f"2021-06-02 18:01:44,303 | INFO | simple-example {APPS_API_VERSION} service.something_generator host 17031 | DONE | response.status=404 | metrics.duration=13.057 | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test | stream.name=simple_example.{APPS_ROUTE_VERSION}.streams.something_event | stream.queue=AUTO",  # noqa: E501
            f"2021-06-02 18:01:44,290 | INFO | client-example {APPS_API_VERSION} count_and_save host 17031 | START | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test",  # noqa: E501
            f"2021-06-02 18:01:44,303 | INFO | client-example {APPS_API_VERSION} count_and_save host 17031 | IGNORED | response.status=404 | metrics.duration=13.057 | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test",  # noqa: E501
            f"2021-06-02 18:01:44,290 | INFO | simple-example {APPS_API_VERSION} streams.something_event host 17031 | START | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test |  stream.name=simple_example.{APPS_ROUTE_VERSION}.streams.something_event.high-prio | stream.queue=high-prio",  # noqa: E501
            f"2021-06-02 18:01:44,303 | INFO | simple-example {APPS_API_VERSION} streams.something_event host 17031 | DONE | response.status=404 | metrics.duration=13.057 | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test | stream.name=simple_example.{APPS_ROUTE_VERSION}.streams.something_event.high-prio | stream.queue=high-prio",  # noqa: E501
            f"2021-06-02 18:01:44,290 | INFO | simple-example {APPS_API_VERSION} streams.process_events host 17031 | START | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test | stream.name=simple_example.{APPS_ROUTE_VERSION}.streams.something_event.high-prio | stream.queue=high-prio",  # noqa: E501
            f"2021-06-02 18:01:44,303 | INFO | simple-example {APPS_API_VERSION} streams.process_events host 17031 | FAILED | response.status=404 | metrics.duration=13.057 | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test |  stream.name=simple_example.{APPS_ROUTE_VERSION}.streams.something_event.high-prio | stream.queue=high-prio",  # noqa: E501
            f"2021-06-02 18:01:44,290 | INFO | simple-example {APPS_API_VERSION} login host 17031 | START | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test | event.app=simple_example.{APPS_ROUTE_VERSION} | event.plugin=basic_auth.{APPS_ROUTE_VERSION}",  # noqa: E501
            f"2021-06-02 18:01:44,303 | INFO | simple-example {APPS_API_VERSION} login host 17031 | DONE | response.status=404 | metrics.duration=13.057 | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test | event.app=simple_example.{APPS_ROUTE_VERSION} | event.plugin=basic_auth.{APPS_ROUTE_VERSION}",  # noqa: E501
        ]
    )
    batch = await _process_log_entries(raw)
    ts = datetime.now(tz=timezone.utc)
    for entry in batch.entries:
        entry.ts = ts.strftime("%Y-%m-%d %H:%M:%S")
        entry.host = socket.gethostname()
        entry.pid = str(os.getpid())
    return batch
