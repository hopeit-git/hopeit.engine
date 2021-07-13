import pytest

from hopeit.server.version import APPS_ROUTE_VERSION
from hopeit.testing.apps import execute_event


@pytest.mark.asyncio
async def test_simple_example_events_diagram(events_graph_data_standard, runtime_apps, plugin_config):
    result = await execute_event(app_config=plugin_config, event_name="apps.events-graph", payload=None)

    assert result.graph.data == events_graph_data_standard
    assert result.options.expanded_view is False


@pytest.mark.asyncio
async def test_simple_example_events_diagram_expanded_view(events_graph_data_expanded,
                                                           runtime_apps, plugin_config):
    result = await execute_event(
        app_config=plugin_config, event_name="apps.events-graph", payload=None, expanded_view="true"
    )

    assert result.graph.data == events_graph_data_expanded
    assert result.options.expanded_view is True


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
