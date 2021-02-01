import pytest  # type: ignore
import uuid
import os
import time
import pathlib
from datetime import datetime, timedelta, timezone

from jwt.exceptions import ExpiredSignatureError, DecodeError, InvalidSignatureError  # type: ignore

import hopeit.server.logger as server_logging
from hopeit.app.config import AppConfig
from hopeit.app.context import EventContext
from hopeit.toolkit import auth
from hopeit.server.config import AuthConfig, AuthType

from mock_app import mock_app_config  # noqa: F401


def test_init():
    config = AuthConfig(
        secrets_location=f"/tmp/{uuid.uuid4()}",
        auth_passphrase='test_passphrase',
        enabled=False
    )
    auth.init(config)
    assert auth.private_key is None
    assert auth.public_key is None

    config.enabled = True

    with pytest.raises(FileNotFoundError):
        auth.init(config)

    config.create_keys = True
    auth.init(config)
    assert auth.private_key is not None
    assert auth.public_key is not None
    assert os.path.exists(pathlib.Path(config.secrets_location) / 'key.pem')
    assert os.path.exists(pathlib.Path(config.secrets_location) / 'key_pub.pem')

    config.create_keys = False
    auth.init(config)
    assert auth.private_key is not None
    assert auth.public_key is not None


def test_token_lifecycle(mock_app_config):  # noqa: F811
    context = _setup_event_context(mock_app_config)
    payload = {
        'test': 'test_value',
        'iat': datetime.now().astimezone(timezone.utc).timestamp(),
        'exp': datetime.now().astimezone(timezone.utc) + timedelta(seconds=2)
    }
    token = auth.new_token(payload)
    assert token is not None
    decoded = auth.validate_token(token, context)
    assert decoded == payload

    time.sleep(3)
    assert auth.validate_token(token, context) is None
    with pytest.raises(ExpiredSignatureError):
        auth.decode_token(token)
    with pytest.raises(DecodeError):
        auth.decode_token('INVALID_TOKEN!!')

    token = auth.new_token(payload={
        'test': 'test_value',
        'iat': datetime.now().astimezone(timezone.utc),
        'exp': datetime.now().astimezone(timezone.utc) + timedelta(seconds=2)
    })
    auth.init(AuthConfig(
        secrets_location=f"/tmp/{uuid.uuid4()}",
        auth_passphrase='test',
        enabled=True,
        create_keys=True
    ))
    assert auth.validate_token(token, context) is None
    with pytest.raises(InvalidSignatureError):
        auth.decode_token(token)


def test_auth_method_unsecured(mock_app_config):  # noqa: F811
    context = _setup_event_context(mock_app_config)
    assert auth.validate_auth_method(
        AuthType.UNSECURED,
        data='',
        context=context) is None
    assert context.auth_info['allowed']
    assert context.auth_info['auth_type'] == AuthType.UNSECURED


def test_auth_method_basic(mock_app_config):  # noqa: F811
    context = _setup_event_context(mock_app_config)
    assert auth.validate_auth_method(
        AuthType.BASIC,
        data='dGVzdDpwYXNz',
        context=context) is None
    assert context.auth_info['allowed']
    assert context.auth_info['auth_type'] == AuthType.BASIC
    assert context.auth_info['payload'] == 'dGVzdDpwYXNz'


def test_auth_method_bearer(mock_app_config):  # noqa: F811
    context = _setup_event_context(mock_app_config)
    payload = {'test': 'test_value', 'exp': datetime.now().astimezone(timezone.utc) + timedelta(seconds=2)}
    token = auth.new_token(payload)
    assert auth.validate_auth_method(
        AuthType.BEARER,
        data=token,
        context=context) is None
    assert context.auth_info['allowed']
    assert context.auth_info['auth_type'] == AuthType.BEARER
    assert context.auth_info['payload'] == auth.decode_token(token)


def test_auth_method_refresh(mock_app_config):  # noqa: F811
    context = _setup_event_context(mock_app_config)
    payload = {'test': 'test_value', 'exp': datetime.now().astimezone(timezone.utc) + timedelta(seconds=2)}
    token = auth.new_token(payload)
    assert auth.validate_auth_method(
        AuthType.REFRESH,
        data=token,
        context=context) is None
    assert context.auth_info['allowed']
    assert context.auth_info['auth_type'] == AuthType.REFRESH
    assert context.auth_info['payload'] == auth.decode_token(token)


def _setup_event_context(mock_app_config: AppConfig) -> EventContext:  # noqa: F811
    _init_engine_logger(mock_app_config)
    assert mock_app_config.server
    mock_app_config.server.auth = AuthConfig(
        secrets_location=f"/tmp/{uuid.uuid4()}",
        auth_passphrase='test_passphrase',
        enabled=True,
        create_keys=True
    )
    auth.init(mock_app_config.server.auth)
    return EventContext(
        app_config=mock_app_config,
        plugin_config=mock_app_config,
        event_name='mock_event',
        track_ids={},
        auth_info={}
    )


def _init_engine_logger(mock_app_config):  # noqa: F811
    logger = server_logging.engine_logger()
    logger.init_server(mock_app_config.server)
    logger.init_app(mock_app_config, plugins=[])
