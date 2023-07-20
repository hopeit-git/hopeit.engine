import asyncio
import pytest
from typing import List, Any
from unittest.mock import MagicMock

import nest_asyncio  # type: ignore
from aiohttp.web_runner import GracefulExit
from aiohttp.web import run_app, Application

from hopeit.server import web, runtime, engine
from hopeit.server.web import parse_args


async def cleanup_test_server():
    runtime.server = engine.Server()
    web.web_server = Application()


def test_port_path():
    args = ['--port=8080', '--path=/tmp/test', '--config-files=engine.json,test.json']
    result = parse_args(args)
    assert result == (None, 8080, '/tmp/test', False, ['engine.json', 'test.json'], None, [], [])


def test_stream_start():
    args = ['--start-streams', '--config-files=test.json']
    result = parse_args(args)
    assert result == (None, 8020, None, True, ['test.json'], None, [], [])


def test_port_only():
    args = ['--port=8020', '--config-files=test.json']
    result = parse_args(args)
    assert result == (None, 8020, None, False, ['test.json'], None, [], [])


def test_path_only():
    args = ['--path=/tmp/test', '--config-files=test.json']
    result = parse_args(args)
    assert result == (None, None, '/tmp/test', False, ['test.json'], None, [], [])


def test_rest_config_only():
    args = ['--config-files=test.json']
    result = parse_args(args)
    assert result == (None, 8020, None, False, ['test.json'], None, [], [])


def test_rest_config_with_host():
    args = ['--host=127.0.0.1', '--config-files=test.json']
    result = parse_args(args)
    assert result == ('127.0.0.1', 8020, None, False, ['test.json'], None, [], [])


def test_config_with_api_file():
    args = ['--config-files=test.json', '--api-file=openapi.json']
    result = parse_args(args)
    assert result == (None, 8020, None, False, ['test.json'], 'openapi.json', [], [])


def test_config_with_api_auto():
    args = ['--config-files=test.json', '--api-auto=0.18;Title;Description']
    result = parse_args(args)
    assert result == (None, 8020, None, False, ['test.json'], None, ['0.18', 'Title', 'Description'], [])


def test_config_with_groups():
    args = ['--config-files=test.json', '--api-file=openapi.json', '--enabled-groups=g1,g2']
    result = parse_args(args)
    assert result == (None, 8020, None, False, ['test.json'], 'openapi.json', [], ['g1', 'g2'])


class MockHooks:
    _server_startup_hook_calls: List[Any] = []
    _app_startup_hook_calls: List[Any] = []
    _stream_startup_hook_calls: List[Any] = []


async def _server_startup_hook(*args, **kwargs):
    MockHooks._server_startup_hook_calls.append(
        [*args, {**kwargs}]
    )


async def _app_startup_hook(*args, **kwargs):
    MockHooks._app_startup_hook_calls.append(
        [*args, {**kwargs}]
    )


async def _stream_startup_hook(*args, **kwargs):
    MockHooks._stream_startup_hook_calls.append(
        [*args, {**kwargs}]
    )


@pytest.mark.parametrize("api_file,api_auto", [
    ('test_api_file.json', []),
    (None, ['0.18', 'Title', 'Description']),
    (None, ['0.18']),
    (None, None)])
@pytest.mark.asyncio
async def test_server_initialization(monkeypatch, api_file, api_auto):
    async def _shutdown(*args, **kwargs):
        await asyncio.sleep(1)
        raise GracefulExit

    def _serve():
        web.init_web_server(
            config_files=['test_server_file.json', 'test_app_file.json', 'test_app_file2.json'],
            api_file=api_file,
            api_auto=api_auto,
            enabled_groups=[],
            start_streams=True
        )
        web.web_server.on_startup.append(_shutdown)
        run_app(web.web_server, host='localhost', port=8020, path=None)

    nest_asyncio.apply()

    _load_engine_config = MagicMock()
    _load_api_file = MagicMock()
    _enable_swagger = MagicMock()
    _register_server_config = MagicMock()
    _register_apps = MagicMock()
    _load_app_config = MagicMock()

    monkeypatch.setattr(web, '_load_engine_config', _load_engine_config)
    monkeypatch.setattr(web.api, 'load_api_file', _load_api_file)
    monkeypatch.setattr(web.api, 'register_server_config', _register_server_config)
    monkeypatch.setattr(web.api, 'register_apps', _register_apps)
    monkeypatch.setattr(web.api, 'enable_swagger', _enable_swagger)
    monkeypatch.setattr(web, '_load_app_config', _load_app_config)
    monkeypatch.setattr(web, 'server_startup_hook', _server_startup_hook)
    monkeypatch.setattr(web, 'app_startup_hook', _app_startup_hook)
    monkeypatch.setattr(web, 'stream_startup_hook', _stream_startup_hook)

    try:
        _serve()
        await cleanup_test_server()
    except Exception as e:
        raise e  # Unexpected error
    finally:
        assert len(MockHooks._server_startup_hook_calls) == 1
        assert len(MockHooks._app_startup_hook_calls) == 2
        assert len(MockHooks._stream_startup_hook_calls) == 2

        assert _load_engine_config.call_args[0] == ('test_server_file.json',)
        if api_file:
            assert _load_api_file.call_args[0] == ('test_api_file.json',)
        assert _register_server_config.call_count == (1 if api_file or api_auto else 0)
        assert _load_app_config.call_args_list[0][0] == ('test_app_file.json',)
        assert _load_app_config.call_args_list[1][0] == ('test_app_file2.json',)
        assert _register_apps.call_count == 1
        assert _enable_swagger.call_count == 1

        MockHooks._stream_startup_hook_calls = []
        MockHooks._server_startup_hook_calls = []
        MockHooks._app_startup_hook_calls = []
