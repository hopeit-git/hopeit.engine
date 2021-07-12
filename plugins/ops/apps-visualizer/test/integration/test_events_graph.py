import pytest

from hopeit.server.version import APPS_ROUTE_VERSION
from hopeit.testing.apps import execute_event


@pytest.mark.asyncio
async def test_simple_example_events_diagram(events_graph_data, runtime_apps, plugin_config):
    result = await execute_event(app_config=plugin_config, event_name="apps.events-graph", payload=None)

    assert result.graph.data == events_graph_data
    assert result.options.expand_queues is False


@pytest.mark.asyncio
async def test_simple_example_events_diagram_expand_queues(events_graph_data,
                                                           runtime_apps, plugin_config):
    result = await execute_event(
        app_config=plugin_config, event_name="apps.events-graph", payload=None, expand_queues="true"
    )
    streams = {
        k: v['data']
        for k, v in result.graph.data.items()
        if "STREAM" in v.get('classes', '')
    }

    s1 = streams[f'>simple_example.{APPS_ROUTE_VERSION}.streams.something_event.AUTO']
    assert s1['id'] == f'>simple_example.{APPS_ROUTE_VERSION}.streams.something_event.AUTO'
    assert s1['content'] == f'simple_example.{APPS_ROUTE_VERSION}\nstreams.something_event'

    s2 = streams[f'>simple_example.{APPS_ROUTE_VERSION}.streams.something_event.high-prio']
    assert s2['id'] == f'>simple_example.{APPS_ROUTE_VERSION}.streams.something_event.high-prio'
    assert s2['content'] == f'simple_example.{APPS_ROUTE_VERSION}\nstreams.something_event.high-prio'

    assert result.options.expand_queues is True


@pytest.mark.asyncio
async def test_simple_example_events_diagram_filter_apps(events_graph_data, plugin_config):
    filtered_events_graph_data = {
        k: v for k, v in events_graph_data.items() if "simple_example" in k
    }
    result = await execute_event(
        app_config=plugin_config, event_name="apps.events-graph", payload=None,
        app_prefix="simple-example"
    )
    assert result.graph.data == filtered_events_graph_data
    assert result.options.app_prefix == "simple-example"
