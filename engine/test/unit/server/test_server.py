import pytest  # type: ignore

from hopeit.app.config import AppConfig
from hopeit.server import runtime
from hopeit.server import engine


from mock_app import mock_app_config  # type: ignore
from mock_plugin import mock_plugin_config  # type: ignore
from mock_engine import MockAppEngine


async def start_server(app_config: AppConfig, plugin: AppConfig) -> engine.Server:
    assert app_config.server
    server = await runtime.server.start(config=app_config.server)
    await server.start_app(app_config=plugin, enabled_groups=[])
    await server.start_app(app_config=app_config, enabled_groups=[])
    return server


async def test_app_start(monkeypatch, mock_app_config, mock_plugin_config):
    monkeypatch.setattr(engine, "AppEngine", MockAppEngine)
    server = await start_server(mock_app_config, mock_plugin_config)
    assert server.app_engine(app_key="mock_app.test").app_config == mock_app_config
    assert server.app_engine(app_key="mock_plugin.test").app_config == mock_plugin_config
    await server.stop()
