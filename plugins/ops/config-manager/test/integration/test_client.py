import pytest

from hopeit.testing.apps import config, create_test_context

from hopeit.config_manager import client

from . import mock_client


@pytest.mark.asyncio
async def test_client(monkeypatch, cluster_apps_response,
                      server1_apps_response, server2_apps_response):

    mock_client(client, monkeypatch, server1_apps_response, server2_apps_response)

    plugin_config = config('plugins/ops/config-manager/config/plugin-config.json')
    context = create_test_context(plugin_config, "cluster-apps-config")
    result = await client.get_apps_config("http://test-server1,http://test-server2", context)

    assert result == cluster_apps_response
