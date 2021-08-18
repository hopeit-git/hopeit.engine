import pytest  # type: ignore
import uuid
import os
import time
import pathlib
from datetime import datetime, timedelta, timezone

from jwt import ExpiredSignatureError, DecodeError, InvalidSignatureError

import hopeit.server.logger as server_logging
from hopeit.app.config import AppConfig
from hopeit.app.context import EventContext
from hopeit.toolkit import auth
from hopeit.server.config import AuthConfig, AuthType

from mock_app import mock_app_config, mock_client_app_config  # noqa: F401


def test_init():
    config = AuthConfig(
        secrets_location=f"/tmp/{uuid.uuid4()}",
        auth_passphrase='test_passphrase',
        enabled=False
    )
    auth.init("test_app", config)
    assert auth.private_keys == {}
    assert auth.public_keys == {}

    config.enabled = True

    with pytest.raises(FileNotFoundError):
        auth.init("test_app", config)

    config.create_keys = True
    auth.init("test_app", config)
    assert "test_app" in auth.private_keys
    assert "test_app" in auth.public_keys
    assert os.path.exists(pathlib.Path(config.secrets_location) / '.private' / 'test_app.pem')
    assert os.path.exists(pathlib.Path(config.secrets_location) / 'public' / 'test_app_pub.pem')

    config.create_keys = False
    auth.init("test_app", config)
    assert "test_app" in auth.private_keys
    assert "test_app" in auth.public_keys


def test_token_lifecycle(mock_app_config):  # noqa: F811
    context = _setup_server_context(mock_app_config)
    payload = {
        'test': 'test_value',
        'iat': datetime.now().astimezone(timezone.utc),
        'exp': datetime.now().astimezone(timezone.utc) + timedelta(seconds=2)
    }
    token = auth.new_token(mock_app_config.app_key(), payload)
    assert token is not None
    decoded = auth.validate_token(token, context)
    assert decoded == {
        'test': 'test_value',
        'iat': int(payload['iat'].timestamp()),
        'exp': int(payload['exp'].timestamp()),
        "app": mock_app_config.app_key()
    }

    time.sleep(3)
    assert auth.validate_token(token, context) is None
    with pytest.raises(ExpiredSignatureError):
        auth.decode_token(token)

    with pytest.raises(DecodeError):
        auth.decode_token('INVALID_TOKEN!!')

    token = auth.new_token(mock_app_config.app_key(), payload={
        'test': 'test_value',
        'iat': datetime.now().astimezone(timezone.utc),
        'exp': datetime.now().astimezone(timezone.utc) + timedelta(seconds=2)
    })
    auth.init(mock_app_config.app_key(), AuthConfig(
        secrets_location=f"/tmp/{uuid.uuid4()}",
        auth_passphrase='test',
        enabled=True,
        create_keys=True
    ))
    assert auth.validate_token(token, context) is None
    with pytest.raises(InvalidSignatureError):
        auth.decode_token(token)


def test_client_tokens(mock_app_config, mock_client_app_config):  # noqa: F811
    server_context = _setup_server_context(mock_app_config)
    assert auth.app_private_key(server_context.app_key) is not None
    assert auth.app_public_key(server_context.app_key) is not None

    client_context = _setup_client_context(mock_client_app_config, mock_app_config, register_client_key=True)
    assert auth.app_private_key(client_context.app_key) is not None
    assert auth.app_public_key(client_context.app_key) is not None

    payload = {
        'test': 'test_value',
        'iat': datetime.now().astimezone(timezone.utc),
        'exp': datetime.now().astimezone(timezone.utc) + timedelta(seconds=2)
    }

    # Client-generated token validated in server
    token = auth.new_token(client_context.app_key, payload)
    assert token is not None

    _switch_auth_context(mock_app_config)
    decoded = auth.validate_token(token, server_context)
    assert decoded == {
        'test': 'test_value',
        'iat': int(payload['iat'].timestamp()),
        'exp': int(payload['exp'].timestamp()),
        "app": client_context.app_key
    }


def test_client_not_registered(mock_app_config, mock_client_app_config):  # noqa: F811
    server_context = _setup_server_context(mock_app_config)
    client_context = _setup_client_context(
        mock_client_app_config, mock_app_config, register_client_key=False
    )

    payload = {
        'test': 'test_value',
        'iat': datetime.now().astimezone(timezone.utc),
        'exp': datetime.now().astimezone(timezone.utc) + timedelta(seconds=2)
    }

    # Client-generated token validated in server
    token = auth.new_token(client_context.app_key, payload)
    assert token is not None

    _switch_auth_context(mock_app_config)
    decoded = auth.validate_token(token, server_context)
    assert decoded is None


def test_auth_method_unsecured(mock_app_config):  # noqa: F811
    context = _setup_server_context(mock_app_config)
    assert auth.validate_auth_method(
        AuthType.UNSECURED,
        data='',
        context=context) is None
    assert context.auth_info['allowed']
    assert context.auth_info['auth_type'] == AuthType.UNSECURED


def test_auth_method_basic(mock_app_config):  # noqa: F811
    context = _setup_server_context(mock_app_config)
    assert auth.validate_auth_method(
        AuthType.BASIC,
        data='dGVzdDpwYXNz',
        context=context) is None
    assert context.auth_info['allowed']
    assert context.auth_info['auth_type'] == AuthType.BASIC
    assert context.auth_info['payload'] == 'dGVzdDpwYXNz'


def test_auth_method_bearer(mock_app_config):  # noqa: F811
    context = _setup_server_context(mock_app_config)
    payload = {
        'test': 'test_value',
        'exp': datetime.now().astimezone(timezone.utc) + timedelta(seconds=2)
    }
    token = auth.new_token(mock_app_config.app_key(), payload)
    assert auth.validate_auth_method(
        AuthType.BEARER,
        data=token,
        context=context) is None
    assert context.auth_info['allowed']
    assert context.auth_info['auth_type'] == AuthType.BEARER
    assert context.auth_info['payload'] == auth.decode_token(token)


def test_auth_method_refresh(mock_app_config):  # noqa: F811
    context = _setup_server_context(mock_app_config)
    payload = {
        'test': 'test_value',
        'exp': datetime.now().astimezone(timezone.utc) + timedelta(seconds=2)
    }
    token = auth.new_token(mock_app_config.app_key(), payload)
    assert auth.validate_auth_method(
        AuthType.REFRESH,
        data=token,
        context=context) is None
    assert context.auth_info['allowed']
    assert context.auth_info['auth_type'] == AuthType.REFRESH
    assert context.auth_info['payload'] == auth.decode_token(token)


def _setup_server_context(app_config: AppConfig) -> EventContext:
    _init_engine_logger(app_config)
    assert app_config.server
    app_config.server.auth = AuthConfig(
        secrets_location=f"/tmp/{uuid.uuid4()}",
        auth_passphrase='test_passphrase',
        enabled=True,
        create_keys=True
    )
    auth.init(app_config.app_key(), app_config.server.auth)
    return EventContext(
        app_config=app_config,
        plugin_config=app_config,
        event_name='mock_event',
        track_ids={},
        auth_info={}
    )


def _setup_client_context(app_config: AppConfig, server_app_config: AppConfig,
                          register_client_key: bool = True) -> EventContext:
    _init_engine_logger(app_config)
    assert app_config.server
    assert server_app_config.server
    app_config.server.auth = AuthConfig(
        secrets_location=f"/tmp/{uuid.uuid4()}",
        auth_passphrase='test_passphrase',
        enabled=True,
        create_keys=True
    )
    auth.init(app_config.app_key(), app_config.server.auth)
    if register_client_key:
        os.rename(
            pathlib.Path(app_config.server.auth.secrets_location) / 'public' / f'{app_config.app_key()}_pub.pem',
            pathlib.Path(server_app_config.server.auth.secrets_location) / 'public' / f'{app_config.app_key()}_pub.pem'
        )
    return EventContext(
        app_config=app_config,
        plugin_config=app_config,
        event_name='mock_event',
        track_ids={},
        auth_info={}
    )


def _switch_auth_context(app_config: AppConfig):
    assert app_config.server
    auth.auth_config = app_config.server.auth
    auth.public_keys = {}  # Forces reloading keys


def _init_engine_logger(mock_app_config):  # noqa: F811
    logger = server_logging.engine_logger()
    logger.init_server(mock_app_config.server)
    logger.init_app(mock_app_config, plugins=[])
