import pytest

from hopeit.app.client import (
    AppConnectionNotFound,
    register_app_connections,
    app_client,
    stop_app_connections,
    app_call,
    app_call_list,
)
from hopeit.testing.apps import create_test_context

from mock_client_app import mock_client_app_config


async def test_register_app_connections(monkeypatch, mocker, mock_client_app_config):
    await register_app_connections(mock_client_app_config)
    context = create_test_context(mock_client_app_config, "mock_client_event")

    client = app_client("test_app_connection", context)

    assert client.app_config == mock_client_app_config
    assert client.app_connection == "test_app_connection"
    assert client.started

    await stop_app_connections(mock_client_app_config.app_key())
    assert client.stopped
    with pytest.raises(AppConnectionNotFound):
        client = app_client("test_app_connection", context)


async def test_app_call(monkeypatch, mocker, mock_client_app_config):
    await register_app_connections(mock_client_app_config)
    context = create_test_context(mock_client_app_config, "mock_client_event")
    result = await app_call(
        "test_app_connection",
        event="test_event",
        datatype=dict,
        payload="payload",
        context=context,
    )
    assert result == {
        "app_connection": "test_app_connection",
        "event": "test_event",
        "payload": "payload",
    }


async def test_app_call_list(monkeypatch, mocker, mock_client_app_config):
    await register_app_connections(mock_client_app_config)
    context = create_test_context(mock_client_app_config, "mock_client_event")
    result = await app_call_list(
        "test_app_connection",
        event="test_event",
        datatype=dict,
        payload="payload",
        context=context,
    )
    assert result == [
        {
            "app_connection": "test_app_connection",
            "event": "test_event",
            "payload": "payload",
        }
    ]


async def test_app_call_invalid_app_connection(monkeypatch, mocker, mock_client_app_config):
    await register_app_connections(mock_client_app_config)
    context = create_test_context(mock_client_app_config, "mock_client_event")
    with pytest.raises(AppConnectionNotFound):
        await app_call(
            "bad_app_connection",
            event="test_event",
            datatype=dict,
            payload="payload",
            context=context,
        )
