import pytest

from hopeit.testing.apps import config, execute_event

from . import mock_client


@pytest.mark.asyncio
async def test_cluster_apps_config(monkeypatch, cluster_apps_response,
                                   server1_apps_response, server2_apps_response):

    def apply_mock_client(module, context):
        mock_client(module.client, monkeypatch, server1_apps_response, server2_apps_response)

    plugin_config = config('plugins/ops/config-manager/config/plugin-config.json')
    result = await execute_event(
        app_config=plugin_config, event_name="cluster-apps-config", payload=None,
        mocks=[apply_mock_client], hosts="http://test-server1,http://test-server2"
    )

    assert result == cluster_apps_response


@pytest.mark.asyncio
async def test_cluster_apps_config_expand_events(monkeypatch, cluster_apps_response_exp,
                                                server1_apps_response_exp, server2_apps_response_exp):

    def apply_mock_client(module, context):
        mock_client(
            module.client, monkeypatch,
            server1_apps_response_exp, server2_apps_response_exp,
            expand_events=True
        )

    plugin_config = config('plugins/ops/config-manager/config/plugin-config.json')
    result = await execute_event(
        app_config=plugin_config, event_name="cluster-apps-config", payload=None,
        mocks=[apply_mock_client], hosts="http://test-server1,http://test-server2",
        expand_events=True
    )

    assert result == cluster_apps_response_exp
