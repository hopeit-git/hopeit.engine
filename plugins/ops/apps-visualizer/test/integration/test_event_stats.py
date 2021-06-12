from typing import Deque
from collections import deque

import pytest

from hopeit.testing.apps import config, execute_event
import hopeit.server.runtime as runtime

from hopeit.log_streamer import LogBatch, LogEntry
from hopeit.apps_visualizer.apps.events_graph import EventsGraphResult

from . import MockServer, APP_VERSION


recent_entries: Deque[LogEntry] = deque()


def mock_recent_entries(module, context):
    setattr(module, "recent_entries", recent_entries)


@pytest.mark.asyncio
async def test_live_stats(monkeypatch, log_entries: LogBatch, events_graph_data):
    app_config = config('apps/examples/simple-example/config/app-config.json')
    monkeypatch.setattr(
        runtime,
        "server",
        MockServer(app_config)
    )
    plugin_config = config('plugins/ops/apps-visualizer/config/plugin-config.json')
    await execute_event(
        app_config=plugin_config, event_name="event-stats.collect", payload=log_entries,
        mocks=[mock_recent_entries]
    )

    result: EventsGraphResult = await execute_event(  # type: ignore
        app_config=plugin_config, event_name="event-stats.live", payload=None
    )

    assert result.graph.data[
        f'edge_simple_example.{APP_VERSION}.query_something.GET'
    ]['classes'] == 'STARTED RECENT'

    assert result.graph.data[
        f'simple_example.{APP_VERSION}.query_something.GET'
    ]['classes'] == 'REQUEST STARTED RECENT'

    assert result.graph.data[
        f'simple_example.{APP_VERSION}.query_something'
    ]['classes'] == 'EVENT STARTED RECENT'
