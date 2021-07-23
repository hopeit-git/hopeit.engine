import pytest

from hopeit.testing.apps import execute_event

from . import mock_runtime


@pytest.mark.asyncio
async def test_site_main(monkeypatch, mock_lock, plugin_config, effective_events):
    async with mock_lock:
        mock_runtime(monkeypatch, effective_events)

        result, page, _ = await execute_event(
            app_config=plugin_config, event_name="site.main", payload=None, postprocess=True
        )

        assert result.options.app_prefix == ''
        assert result.options.host_filter == ''
        assert result.options.expanded_view is False
        assert result.options.live is False

        assert '{{ app_prefix }}' not in page
        assert '{{ host_filter }}' not in page
        assert '{{ view_link }}' not in page
        assert '{{ live_link }}' not in page
        assert '{{ refresh_endpoint }}' not in page
        assert '{{ view_type }}' not in page
        assert '{{ live_type }}' not in page
