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
        f'simple_example.{APP_VERSION}.query_something.GET'
    ]['classes'] == 'RECENT REQUEST STARTED'

    assert result.graph.data[
        f'simple_example.{APP_VERSION}.query_something'
    ]['classes'] == 'EVENT RECENT STARTED'

    assert result.graph.data[
        f'simple_example.{APP_VERSION}.save_something.POST'
    ]['classes'] == 'PENDING RECENT REQUEST STARTED'

    assert result.graph.data[
        f'simple_example.{APP_VERSION}.save_something'
    ]['classes'] == 'EVENT PENDING RECENT STARTED'

    assert result.graph.data[
        f'simple_example.{APP_VERSION}.service.something_generator'
    ]['classes'] == 'EVENT RECENT STARTED'

    assert result.graph.data[
        f'>simple_example.{APP_VERSION}.streams.something_event'
    ]['classes'] == 'RECENT STARTED STREAM'

    assert result.graph.data[
        f'simple_example.{APP_VERSION}.streams.something_event.POST'
    ]['classes'] == 'RECENT REQUEST STARTED'

    assert result.graph.data[
        f'simple_example.{APP_VERSION}.streams.something_event'
    ]['classes'] == 'EVENT RECENT STARTED'

    assert result.graph.data[
        f'simple_example.{APP_VERSION}.streams.process_events'
    ]['classes'] == 'EVENT FAILED RECENT STARTED'

    assert result.graph.data[
        f'edge_simple_example.{APP_VERSION}.query_something.GET'
    ]['classes'] == 'RECENT STARTED'

    assert result.graph.data[
        f'edge_simple_example.{APP_VERSION}.save_something.POST'
    ]['classes'] == 'PENDING RECENT STARTED'

    assert result.graph.data[
        f'edge_simple_example.{APP_VERSION}.streams.process_events.'
        f'simple_example.{APP_VERSION}.streams.something_event.high-prio'
    ]['classes'] == 'FAILED RECENT STARTED'

    assert result.graph.data[
        f'edge_simple_example.{APP_VERSION}.streams.process_events.'
        f'simple_example.{APP_VERSION}.streams.something_event.AUTO'
    ]['classes'] == 'FAILED RECENT STARTED'

    assert result.graph.data[
        f'edge_simple_example.{APP_VERSION}.streams.something_event.POST'
    ]['classes'] == 'RECENT STARTED'

    assert result.graph.data[
        f'edge_simple_example.{APP_VERSION}.streams.something_event.'
        f'simple_example.{APP_VERSION}.streams.something_event.high-prio'
    ]['classes'] == 'RECENT STARTED'


@pytest.mark.asyncio
async def test_live_stats_expanded_view(monkeypatch, log_entries: LogBatch, events_graph_data):
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
        app_config=plugin_config, event_name="event-stats.live", payload=None,
        expand_queues=True
    )

    assert result.graph.data[
        f'simple_example.{APP_VERSION}.query_something.GET'
    ]['classes'] == 'RECENT REQUEST STARTED'

    assert result.graph.data[
        f'simple_example.{APP_VERSION}.query_something'
    ]['classes'] == 'EVENT RECENT STARTED'

    assert result.graph.data[
        f'simple_example.{APP_VERSION}.save_something.POST'
    ]['classes'] == 'PENDING RECENT REQUEST STARTED'

    assert result.graph.data[
        f'simple_example.{APP_VERSION}.save_something'
    ]['classes'] == 'EVENT PENDING RECENT STARTED'

    assert result.graph.data[
        f'>simple_example.{APP_VERSION}.streams.something_event.AUTO'
    ]['classes'] == 'RECENT STARTED STREAM'

    assert result.graph.data[
        f'simple_example.{APP_VERSION}.service.something_generator'
    ]['classes'] == 'EVENT RECENT STARTED'

    assert result.graph.data[
        f'simple_example.{APP_VERSION}.streams.something_event.POST'
    ]['classes'] == 'RECENT REQUEST STARTED'

    assert result.graph.data[
        f'>simple_example.{APP_VERSION}.streams.something_event.high-prio'
    ]['classes'] == 'RECENT STARTED STREAM'

    assert result.graph.data[
        f'simple_example.{APP_VERSION}.streams.something_event'
    ]['classes'] == 'EVENT RECENT STARTED'

    assert result.graph.data[
        f'simple_example.{APP_VERSION}.streams.process_events'
    ]['classes'] == 'EVENT FAILED RECENT STARTED'

    assert result.graph.data[
        f'edge_simple_example.{APP_VERSION}.query_something.GET'
    ]['classes'] == 'RECENT STARTED'

    assert result.graph.data[
        f'edge_simple_example.{APP_VERSION}.save_something.POST'
    ]['classes'] == 'PENDING RECENT STARTED'

    assert result.graph.data[
        f'edge_simple_example.{APP_VERSION}.streams.process_events.'
        f'simple_example.{APP_VERSION}.streams.something_event.AUTO'
    ]['classes'] == 'FAILED RECENT STARTED'

    assert result.graph.data[
        f'edge_simple_example.{APP_VERSION}.service.something_generator.'
        f'simple_example.{APP_VERSION}.streams.something_event.AUTO'
    ]['classes'] == 'RECENT STARTED'

    assert result.graph.data[
        f'edge_simple_example.{APP_VERSION}.streams.something_event.POST'
    ]['classes'] == 'RECENT STARTED'

    assert result.graph.data[
        f'edge_simple_example.{APP_VERSION}.streams.process_events.'
        f'simple_example.{APP_VERSION}.streams.something_event.high-prio.high-prio'
    ]['classes'] == 'FAILED RECENT STARTED'

    assert result.graph.data[
        f'edge_simple_example.{APP_VERSION}.streams.something_event.'
        f'simple_example.{APP_VERSION}.streams.something_event.high-prio.high-prio'
    ]['classes'] == 'RECENT STARTED'
