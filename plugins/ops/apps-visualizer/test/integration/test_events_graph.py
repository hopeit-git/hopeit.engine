import pytest

from hopeit.testing.apps import config, execute_event
import hopeit.server.runtime as runtime

from . import MockServer, APP_VERSION


@pytest.mark.asyncio
async def test_simple_example_events_diagram(monkeypatch, events_graph_data):
    print()
    print(events_graph_data)
    print()
    app_config = config('apps/examples/simple-example/config/app-config.json')
    monkeypatch.setattr(
        runtime,
        "server",
        MockServer(app_config)
    )

    plugin_config = config('plugins/ops/apps-visualizer/config/plugin-config.json')
    result = await execute_event(app_config=plugin_config, event_name="events-graph", payload=None)
    print(dir(result))
    assert result.graph.data == events_graph_data
    assert result.options.expand_queues is False


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
    streams = {
        x['data']['id']: x['data']
        for x in result.graph.data
        if "STREAM" in x.get('classes', '')
    }

    s1 = streams[f'simple_example.{APP_VERSION}.streams.something_event.AUTO']
    assert s1['id'] == f'simple_example.{APP_VERSION}.streams.something_event.AUTO'
    assert s1['content'] == f'simple_example.{APP_VERSION}\nstreams.something_event'

    s2 = streams[f'simple_example.{APP_VERSION}.streams.something_event.high-prio']
    assert s2['id'] == f'simple_example.{APP_VERSION}.streams.something_event.high-prio'
    assert s2['content'] == f'simple_example.{APP_VERSION}\nstreams.something_event.high-prio'

    assert result.options.expand_queues is True


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
    assert result.graph.data == events_graph_data
