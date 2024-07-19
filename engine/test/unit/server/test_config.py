import os

import pytest  # type: ignore

from hopeit.server.config import ServerConfig, StreamsConfig, LoggingConfig, AuthConfig
from hopeit.server.config import parse_server_config_json


@pytest.fixture
def valid_config_json() -> str:
    return """
{
    "streams": {
        "connection_str": "${TEST_REDIS_HOST}:6379"
    },
    "logging": {
        "log_level": "DEBUG",
        "log_path": "/tmp"
    },
    "auth": {
        "secrets_location": "/tmp",
        "auth_passphrase": "test"
    }
}
"""


@pytest.fixture
def valid_result_engine_config() -> ServerConfig:
    return ServerConfig(
        streams=StreamsConfig(connection_str="test_redis_url:6379"),
        logging=LoggingConfig(log_level="DEBUG", log_path="/tmp"),
        auth=AuthConfig(secrets_location="/tmp", auth_passphrase="test"),
    )


def _get_env_mock(var_name, default=None):
    if var_name == "TEST_REDIS_HOST":
        return "test_redis_url"
    return None


def _get_env_missing_mock(var_name, default=None):
    return None


def test_parse_engine_config_json(
    monkeypatch, valid_config_json: str, valid_result_engine_config: ServerConfig
):
    monkeypatch.setattr(os, "getenv", _get_env_mock)
    config = parse_server_config_json(valid_config_json)
    assert config == valid_result_engine_config


def test_missing_env_var_fails(monkeypatch, valid_config_json: str):
    monkeypatch.setattr(os, "getenv", _get_env_missing_mock)
    with pytest.raises(AssertionError):
        parse_server_config_json(valid_config_json)
