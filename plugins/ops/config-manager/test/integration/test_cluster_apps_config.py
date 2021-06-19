import pytest

from hopeit.server import runtime
from hopeit.testing.apps import config, execute_event

from . import MockServer, MockClientSession, APP_VERSION


@pytest.mark.asyncio
async def test_cluster_apps_config(monkeypatch, cluster_apps_response,
                                   server1_apps_response, server2_apps_response):
    app_config = config('apps/examples/simple-example/config/app-config.json')
    monkeypatch.setattr(
        runtime,
        "server",
        MockServer(app_config)
    )

    def mock_client(module, context):
        url_pattern = "{}/api/config-manager/{}/runtime-apps-config?url={}"
        url1 = url_pattern.format("http://test-server1", APP_VERSION, "http://test-server1")
        url2 = url_pattern.format("http://test-server2", APP_VERSION, "http://test-server2")
        monkeypatch.setattr(module.aiohttp, 'ClientSession', MockClientSession.setup(
            responses={
                url1: server1_apps_response,
                url2: server2_apps_response
            }
        ))

    plugin_config = config('plugins/ops/config-manager/config/plugin-config.json')
    result = await execute_event(
        app_config=plugin_config, event_name="cluster-apps-config", payload=None,
        mocks=[mock_client], hosts="http://test-server1,http://test-server2"
    )

    assert result == cluster_apps_response
