
from hopeit.config_manager import ServerStatus, client

from . import mock_client, mock_context, app_config
import hopeit.server.logger as server_logging


async def test_client(
    monkeypatch, cluster_apps_response, server1_apps_response, server2_apps_response
):
    _init_engine_logger(app_config())
    context = mock_context(event_name="cluster_apps_config")

    mock_client(client, monkeypatch, server1_apps_response, server2_apps_response)

    result = await client.get_apps_config(
        "http://test-server1,http://test-server2", context, expand_events=False
    )

    assert result == cluster_apps_response


async def test_client_timeout(
    monkeypatch, cluster_apps_response, server1_apps_response, server2_apps_response
):
    _init_engine_logger(app_config())

    mock_client(client, monkeypatch, server1_apps_response, server2_apps_response)
    context = mock_context(event_name="cluster_apps_config", timeout=5.0)

    result = await client.get_apps_config(
        "http://test-server1,http://test-server2", context, expand_events=False
    )
    assert result.apps == {}
    assert result.server_status == {
        "http://test-server1": ServerStatus.ERROR,
        "http://test-server2": ServerStatus.ERROR,
    }


async def test_client_expand_events(
    monkeypatch, effective_events_example, server1_apps_response, server2_apps_response
):
    _init_engine_logger(app_config())
    mock_client(
        client,
        monkeypatch,
        server1_apps_response,
        server2_apps_response,
        effective_events_example,
    )
    context = mock_context(event_name="cluster_apps_config")
    result = await client.get_apps_config(
        "http://test-server1,http://test-server2", context, expand_events=True
    )

    for _, v in result.apps.items():
        assert v.effective_events == effective_events_example


async def test_client_ignore_hosts_errors(
    monkeypatch, cluster_apps_response, server1_apps_response, server2_apps_response
):
    _init_engine_logger(app_config())
    mock_client(client, monkeypatch, server1_apps_response, server2_apps_response)
    context = mock_context(event_name="cluster_apps_config")
    result = await client.get_apps_config(
        "http://test-server1,http://test-server2,http://test-server-error",
        context,
        expand_events=False,
    )

    assert result.apps == cluster_apps_response.apps
    assert result.server_status == {
        "http://test-server1": ServerStatus.ALIVE,
        "http://test-server2": ServerStatus.ALIVE,
        "http://test-server-error": ServerStatus.ERROR,
    }


def _init_engine_logger(mock_app_config):  # noqa: F811
    logger = server_logging.engine_logger()
    logger.init_server(mock_app_config.server)
    logger.init_app(mock_app_config, plugins=[])
