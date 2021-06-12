import json
import os
from pathlib import Path
from datetime import datetime

import pytest
from hopeit.testing.apps import config, execute_event
from hopeit.log_streamer import LogRawBatch, LogBatch

from . import APP_VERSION


@pytest.fixture
def events_graph_data():
    with open(Path(os.path.dirname(os.path.realpath(__file__))) / 'events_graph_data.json') as f:
        json_str = f.read().replace("${APP_VERSION}", APP_VERSION)
        return json.loads(json_str)


async def _process_log_entries(raw: LogRawBatch) -> LogBatch:
    plugin_config = config('plugins/ops/log-streamer/config/plugin-config.json')
    return await execute_event(plugin_config, "log_reader", payload=raw)  # type: ignore


@pytest.fixture
async def log_entries() -> LogBatch:
    raw = LogRawBatch(data=[
        "2021-06-02 18:01:44,290 | INFO | simple-example 0.5 query_something host 17031 | START | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test",  # noqa: E501
        "2021-06-02 18:01:44,303 | INFO | simple-example 0.5 query_something host 17031 | DONE | response.status=404 | metrics.duration=13.057 | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test"  # noqa: E501
    ])
    batch = await _process_log_entries(raw)
    for entry in batch.entries:
        entry.ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return batch
