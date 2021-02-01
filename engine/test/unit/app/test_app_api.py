from typing import Optional

import pytest

import hopeit.app.api as api
from hopeit.app.config import EventType
from hopeit.server.api import APIError
from mock_app import mock_app_api_get, MockData, mock_app_api_post, mock_app_api_get_list  # type: ignore
from mock_app import mock_api_app_config, mock_api_spec  # type: ignore  # noqa: F401


def test_api_from_config(monkeypatch, mock_api_spec, mock_api_app_config):  # noqa: F811
    monkeypatch.setattr(api, 'spec', mock_api_spec)
    spec = api.api_from_config(
        mock_app_api_get, app_config=mock_api_app_config, event_name='mock-app-api-get', plugin=None)
    assert spec == mock_api_spec['paths']['/api/mock-app-api/test/mock-app-api']['get']


def test_api_from_config_missing(monkeypatch, mock_api_spec, mock_api_app_config):  # noqa: F811
    monkeypatch.setattr(api, 'spec', mock_api_spec)
    with pytest.raises(APIError):
        api.api_from_config(
            mock_app_api_get, app_config=mock_api_app_config, event_name='mock-app-noapi', plugin=None)

    mock_api_app_config.events['mock-app-api-get-list'].type = EventType.POST
    with pytest.raises(APIError):
        api.api_from_config(
            mock_app_api_get_list, app_config=mock_api_app_config, event_name='mock-app-api-get-list', plugin=None)


def test_event_api(monkeypatch, mock_api_spec, mock_api_app_config):  # noqa: F811
    monkeypatch.setattr(api, 'spec', mock_api_spec)
    spec = api.event_api(
        payload=(str, "Payload"),
        query_args=[('arg1', Optional[int], "Argument 1")],
        responses={200: (MockData, "MockData result")}
    )(mock_app_api_get, app_config=mock_api_app_config, event_name='mock-app-api-get', plugin=None)
    assert spec['description'] == \
        mock_api_spec['paths']['/api/mock-app-api/test/mock-app-api']['get']['description']
    assert spec['parameters'][0] == \
        mock_api_spec['paths']['/api/mock-app-api/test/mock-app-api']['get']['parameters'][0]
    assert spec['responses'] == \
        mock_api_spec['paths']['/api/mock-app-api/test/mock-app-api']['get']['responses']


def test_event_api_post(monkeypatch, mock_api_spec, mock_api_app_config):  # noqa: F811
    monkeypatch.setattr(api, 'spec', mock_api_spec)
    mock_api_spec['paths']['/api/mock-app-api/test/mock-app-api']['post']['parameters'][0]['description'] = \
        'arg1'
    mock_api_spec['paths']['/api/mock-app-api/test/mock-app-api']['post']['requestBody']['description'] = \
        'MockData'
    spec = api.event_api(
        description="Description Test app api part 2",
        payload=MockData,
        query_args=['arg1'],
        responses={200: int}
    )(mock_app_api_post, app_config=mock_api_app_config, event_name='mock-app-api-post', plugin=None)
    assert spec['summary'] == \
        mock_api_spec['paths']['/api/mock-app-api/test/mock-app-api']['post']['summary']
    assert spec['description'] == \
        mock_api_spec['paths']['/api/mock-app-api/test/mock-app-api']['post']['description']
    assert spec['parameters'][0] == \
        mock_api_spec['paths']['/api/mock-app-api/test/mock-app-api']['post']['parameters'][0]
    assert spec['requestBody'] == \
        mock_api_spec['paths']['/api/mock-app-api/test/mock-app-api']['post']['requestBody']
    assert spec['responses'] == \
        mock_api_spec['paths']['/api/mock-app-api/test/mock-app-api']['post']['responses']


def test_app_base_route_name(mock_api_app_config):  # noqa: F811
    assert api.app_base_route_name(mock_api_app_config.app) == "/api/mock-app-api/test"
    assert api.app_base_route_name(mock_api_app_config.app, plugin=mock_api_app_config.app) == \
        "/api/mock-app-api/test/mock-app-api/test"
