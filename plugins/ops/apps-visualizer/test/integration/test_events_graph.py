
from hopeit.testing.apps import execute_event

from . import mock_runtime


async def test_simple_example_events_diagram(
    monkeypatch, mock_lock, events_graph_data_standard, plugin_config, effective_events
):
    async with mock_lock:
        mock_runtime(monkeypatch, effective_events)
        result = await execute_event(
            app_config=plugin_config, event_name="apps.events-graph", payload=None
        )
        assert result.graph.data == events_graph_data_standard
        assert result.options.expanded_view is False


async def test_simple_example_events_diagram_expanded_view(
    monkeypatch, mock_lock, events_graph_data_expanded, plugin_config, effective_events
):
    async with mock_lock:
        mock_runtime(monkeypatch, effective_events)
        result = await execute_event(
            app_config=plugin_config,
            event_name="apps.events-graph",
            payload=None,
            expanded_view="true",
        )

        assert result.graph.data == events_graph_data_expanded
        assert result.options.expanded_view is True


async def test_simple_example_events_diagram_filter_apps(
    monkeypatch, mock_lock, events_graph_data_standard, plugin_config, effective_events
):
    async with mock_lock:
        mock_runtime(monkeypatch, effective_events)
        filtered_events_graph_data = {
            k: v for k, v in events_graph_data_standard.items() if "simple_example" in k
        }
        result = await execute_event(
            app_config=plugin_config,
            event_name="apps.events-graph",
            payload=None,
            app_prefix="simple-example",
        )

        assert result.graph.data == filtered_events_graph_data
        assert result.options.app_prefix == "simple-example"
