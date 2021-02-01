import pytest  # type: ignore

from hopeit.app.config import AppConfig
from hopeit.server.engine import Server, AppEngine

from mock_app import mock_app_config  # type: ignore  # noqa: F401
from mock_plugin import mock_plugin_config  # type: ignore  # noqa: F401
from mock_engine import MockAppEngine


async def start_server(app_config: AppConfig,
                       plugin: AppConfig) -> Server:
    assert app_config.server
    server = await Server().start(config=app_config.server)
    await server.start_app(plugin)
    await server.start_app(app_config)
    return server


@pytest.mark.asyncio
async def test_app_start(monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    monkeypatch.setattr(AppEngine, '__init__', MockAppEngine.__init__)
    monkeypatch.setattr(AppEngine, 'start', MockAppEngine.start)
    monkeypatch.setattr(AppEngine, 'stop', MockAppEngine.stop)
    server = await start_server(mock_app_config, mock_plugin_config)
    assert server.app_engine(app_key='mock_app.test').app_config == mock_app_config
    assert server.app_engine(app_key='mock_plugin.test').app_config == mock_plugin_config
    await server.stop()
