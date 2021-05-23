import json

import pytest

from hopeit.testing.apps import config, execute_event
import hopeit.server.runtime as runtime

from . import MockServer


@pytest.mark.asyncio
async def test_simple_example_events_diagram(monkeypatch, events_graph_data):
    app_config = config('apps/examples/simple-example/config/app-config.json')
    monkeypatch.setattr(
        runtime,
        "server",
        MockServer(app_config)
    )

    plugin_config = config('plugins/ops/apps-visualizer/config/plugin-config.json')
    result = await execute_event(app_config=plugin_config, event_name="events-graph", payload=None)

    assert json.loads(result) == events_graph_data


@pytest.mark.asyncio
async def test_simple_example_events_diagram_expand_queues(monkeypatch, events_graph_data):
    app_config = config('apps/examples/simple-example/config/app-config.json')
    monkeypatch.setattr(
        runtime,
        "server",
        MockServer(app_config)
    )

    plugin_config = config('plugins/ops/apps-visualizer/config/plugin-config.json')
    result = await execute_event(
        app_config=plugin_config, event_name="events-graph", payload=None, expand_queues="true"
    )
    data = json.loads(result)
    streams = {x['data']['id'] for x in data if x['data'].get('group') == "STREAM"}
    assert 'simple_example.0x4.streams.something_event.AUTO' in streams
    assert 'simple_example.0x4.streams.something_event.high-prio' in streams


@pytest.mark.asyncio
async def test_simple_example_events_diagram_filter_apps(monkeypatch, events_graph_data):
    app_config = config('apps/examples/simple-example/config/app-config.json')
    plugin_config = config('plugins/ops/apps-visualizer/config/plugin-config.json')

    monkeypatch.setattr(
        runtime,
        "server",
        MockServer(app_config, plugin_config)
    )
    result = await execute_event(
        app_config=plugin_config, event_name="events-graph", payload=None,
        app_prefix="simple-example"
    )
    assert json.loads(result) == events_graph_data
