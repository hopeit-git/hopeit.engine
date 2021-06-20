import pytest

from hopeit.testing.apps import execute_event


@pytest.mark.asyncio
async def test_site_main(monkeypatch, events_graph_data, runtime_apps, plugin_config):
    result, page, _ = await execute_event(
        app_config=plugin_config, event_name="site.main", payload=None, postprocess=True
    )

    assert result.runtime_apps == runtime_apps
    assert result.options.app_prefix == ''
    assert result.options.host_filter == ''
    assert result.options.expand_queues is False
    assert result.options.live is False

    assert '{{ app_prefix }}' not in page
    assert '{{ host_filter }}' not in page
    assert '{{ view_link }}' not in page
    assert '{{ live_link }}' not in page
    assert '{{ refresh_endpoint }}' not in page
    assert '{{ view_type }}' not in page
    assert '{{ live_type }}' not in page
