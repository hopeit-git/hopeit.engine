import json
import os
import uuid
from copy import deepcopy

import pytest
from aiohttp import web
from aiohttp_swagger3.swagger_route import SwaggerRoute  # type: ignore

from hopeit.server import api
from hopeit.server.api import app_route_name, APIError
from mock_app import mock_api_spec, mock_api_app_config, mock_app_api_generated  # type: ignore  # noqa: F401
from mock_plugin import mock_plugin_config  # type: ignore  # noqa: F401


def test_init_empty_spec(mock_api_spec):  # noqa: F811
    api.clear()
    api.init_empty_spec(api_version=mock_api_spec['info']['version'],
                        title=mock_api_spec['info']['title'],
                        description=mock_api_spec['info']['description'])
    assert api.spec == {
        'openapi': api.OPEN_API_VERSION,
        'info': mock_api_spec['info'],
        'paths': {}
    }
    assert api.static_spec == api.spec


def test_generate_mode(mock_api_app_config, mock_api_spec, mock_plugin_config, mock_app_api_generated):  # noqa: F811
    api.clear()
    _init_api(mock_api_app_config, mock_api_spec, plugin=mock_plugin_config, init_server=True, init_apps=True,
              generate_mode=True)
    generated_spec = deepcopy(mock_api_spec)
    generated_spec['paths'].update(mock_app_api_generated)
    assert api.spec == generated_spec


def test_load_api_file(mock_api_spec):  # noqa: F811
    api.clear()
    file_name = f"/tmp/{str(uuid.uuid4())}.json"
    with open(file_name, 'w') as fp:
        json.dump(mock_api_spec, fp)
    api.load_api_file(file_name)
    assert api.spec == mock_api_spec
    assert api.static_spec == mock_api_spec
    assert id(api.spec) != id(api.static_spec)
    os.remove(file_name)


def test_save_api_file(mock_api_spec):  # noqa: F811
    api.clear()
    file_name = f"/tmp/{str(uuid.uuid4())}.json"
    api.spec = mock_api_spec
    api.static_spec = deepcopy(mock_api_spec)
    api.save_api_file(file_name, api_version=mock_api_spec['info']['version'])
    with open(file_name, 'r') as fp:
        check_spec = json.load(fp)
    assert check_spec == mock_api_spec

    with pytest.raises(APIError):
        api.static_spec['info']['title'] = 'Simulating API Change'
        api.save_api_file(file_name, api_version=mock_api_spec['info']['version'])

    api.save_api_file(file_name, api_version='9.9.9')
    with open(file_name, 'r') as fp:
        check_spec = json.load(fp)
    assert check_spec == mock_api_spec
    assert check_spec['info']['version'] == '9.9.9'
    os.remove(file_name)


def _init_api(mock_api_app_config, mock_api_spec, plugin=None,  # noqa: F811
              init_server=False, init_apps=False, init_swagger=False,
              generate_mode=False):
    api.clear()
    if generate_mode:
        api.setup(generate_mode=True)
    api.init_empty_spec(api_version=mock_api_spec['info']['version'],
                        title=mock_api_spec['info']['title'],
                        description=mock_api_spec['info']['description'])
    server_config = mock_api_app_config.server
    if init_server:
        api.register_server_config(server_config)
    if init_apps:
        apps = [mock_api_app_config]
        if plugin:
            apps.append(plugin)
        api.register_apps(apps)
    if init_swagger:
        api.static_spec = deepcopy(api.spec)
        api.enable_swagger(mock_api_app_config.server, web.Application())


def test_register_server_config(mock_api_app_config, mock_api_spec):  # noqa: F811
    _init_api(mock_api_app_config, mock_api_spec, init_server=True)
    assert api.spec['components']['securitySchemes'] == {
        'auth.basic': {'scheme': 'basic', 'type': 'http'},
        'auth.bearer': {'scheme': 'bearer', 'type': 'http'}
    }
    assert api.spec['security'] == [{'auth.bearer': []}]


def test_register_apps(mock_api_app_config, mock_api_spec, mock_plugin_config):  # noqa: F811
    _init_api(mock_api_app_config, mock_api_spec, plugin=mock_plugin_config, init_server=True, init_apps=True)
    assert api.spec['components']['schemas'] == mock_api_spec['components']['schemas']
    assert api.spec['paths'] == mock_api_spec['paths']


async def test_enable_swagger(mock_api_app_config, mock_api_spec, mock_plugin_config):  # noqa: F811
    _init_api(mock_api_app_config, mock_api_spec, plugin=mock_plugin_config,
              init_server=True, init_apps=True, init_swagger=True)
    assert api.swagger is not None


async def test_enable_swagger_incompatible_api(mock_api_app_config, mock_api_spec, mock_plugin_config):  # noqa: F811
    _init_api(mock_api_app_config, mock_api_spec, plugin=mock_plugin_config,
              init_server=True, init_apps=True, init_swagger=False)

    with pytest.raises(APIError):
        api.static_spec['info']['title'] = 'Simulating API Change'
        api.enable_swagger(server_config=mock_api_app_config.server, app=web.Application())


async def _test_handler_get(request):
    return "get"


async def _test_handler_post(request):
    return "post"


def test_add_route_auto_name(mock_api_app_config, mock_api_spec, mock_plugin_config):  # noqa: F811
    _init_api(mock_api_app_config, mock_api_spec, plugin=mock_plugin_config,
              init_server=True, init_apps=True, init_swagger=True)
    route = app_route_name(mock_api_app_config.app, event_name='mock-app-api-get-list')
    handler = api.add_route('get', route, _test_handler_get)
    assert isinstance(handler.args[0], SwaggerRoute)
    route = app_route_name(mock_api_app_config.app, event_name='mock-app-noapi')
    handler = api.add_route('get', route, _test_handler_get)
    assert handler is _test_handler_get


def test_add_route_override_name(mock_api_app_config, mock_api_spec, mock_plugin_config):  # noqa: F811
    _init_api(mock_api_app_config, mock_api_spec, plugin=mock_plugin_config,
              init_server=True, init_apps=True, init_swagger=True)
    route = app_route_name(mock_api_app_config.app, event_name='mock-app-api-get',
                           override_route_name='mock-app-api/test/mock-app-api')
    handler = api.add_route('get', route, _test_handler_get)
    assert isinstance(handler.args[0], SwaggerRoute)
    assert handler.args[0].path == route
    handler = api.add_route('post', route, _test_handler_post)
    assert isinstance(handler.args[0], SwaggerRoute)
    assert handler.args[0].path == route
    assert api.spec['paths']['/api/mock-app-api/test/mock-app-api'].keys() == {'get', 'post'}
    route = app_route_name(mock_api_app_config.app, event_name='mock-app-noapi')
    handler = api.add_route('get', route, _test_handler_get)
    assert handler is _test_handler_get


def test_api_disabled(mock_api_app_config):  # noqa: F811
    api.clear()
    api.register_server_config(mock_api_app_config.server)
    assert api.spec is None
    apps = [mock_api_app_config]
    app = web.Application()
    api.register_apps(apps)
    api.enable_swagger(mock_api_app_config.server, app)
    assert api.spec is None
    route = app_route_name(mock_api_app_config.app, event_name='mock-app-api-get')
    handler = api.add_route('get', route, _test_handler_get)
    assert handler is _test_handler_get
    route = app_route_name(mock_api_app_config.app, event_name='mock-app-noapi')
    handler = api.add_route('get', route, _test_handler_get)
    assert handler is _test_handler_get


async def test_remove_metadata(mock_api_app_config, mock_api_spec, mock_plugin_config):  # noqa: F811
    _init_api(mock_api_app_config, mock_api_spec, plugin=mock_plugin_config,
              init_server=True, init_apps=True, init_swagger=True)

    assert "metadata" not in api.spec["components"]["schemas"]["MockData"]["properties"]["value"]
    assert "title" in api.spec["components"]["schemas"]["MockData"]["properties"]["value"]
    assert "type" in api.spec["components"]["schemas"]["MockData"]["properties"]["value"]
