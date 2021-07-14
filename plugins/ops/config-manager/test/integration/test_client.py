import pytest

from hopeit.config_manager import ServerStatus, client

from . import mock_client


@pytest.mark.asyncio
async def test_client(monkeypatch, cluster_apps_response,
                      server1_apps_response, server2_apps_response):

    mock_client(client, monkeypatch, server1_apps_response, server2_apps_response)

    result = await client.get_apps_config("http://test-server1,http://test-server2", expand_events=False)

    assert result == cluster_apps_response


@pytest.mark.asyncio
async def test_client_expand_events(monkeypatch, cluster_apps_response_exp,
                                    server1_apps_response_exp, server2_apps_response_exp):

    mock_client(client, monkeypatch, server1_apps_response_exp, server2_apps_response_exp, expand_events=True)

    result = await client.get_apps_config("http://test-server1,http://test-server2", expand_events=True)

    assert result == cluster_apps_response_exp


@pytest.mark.asyncio
async def test_client_ignore_hosts_errors(monkeypatch, cluster_apps_response,
                                          server1_apps_response, server2_apps_response):

    mock_client(client, monkeypatch, server1_apps_response, server2_apps_response)

    result = await client.get_apps_config(
        "http://test-server1,http://test-server2,http://test-server-error",
        expand_events=False
    )

    assert result.apps == cluster_apps_response.apps
    assert result.server_status == {
        "http://test-server1": ServerStatus.ALIVE,
        "http://test-server2": ServerStatus.ALIVE,
        "http://test-server-error": ServerStatus.ERROR,
    }
