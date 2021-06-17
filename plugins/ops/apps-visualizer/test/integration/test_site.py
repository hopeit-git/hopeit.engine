import pytest

from hopeit.testing.apps import config, execute_event
import hopeit.server.runtime as runtime

from . import MockServer


def check_replacements(page: str):
    assert '{{ app_items }}' not in page
    assert '{{ app_prefix }}' not in page
    assert '{{ view_link }}' not in page
    assert '{{ live_link }}' not in page
    assert '{{ refresh_endpoint }}' not in page
    assert '{{ view_type }}' not in page
    assert '{{ live_type }}' not in page


@pytest.mark.asyncio
async def test_site_main(monkeypatch, events_graph_data):
    app_config = config('apps/examples/simple-example/config/app-config.json')
    monkeypatch.setattr(
        runtime,
        "server",
        MockServer(app_config)
    )

    plugin_config = config('plugins/ops/apps-visualizer/config/plugin-config.json')
    result, page, _ = await execute_event(
        app_config=plugin_config, event_name="site.main", payload=None, postprocess=True
    )
    assert result.runtime_apps.apps == [app_config]
    assert result.options.app_prefix == ''
    assert result.options.expand_queues is False
    assert result.options.live is False

    check_replacements(page)
