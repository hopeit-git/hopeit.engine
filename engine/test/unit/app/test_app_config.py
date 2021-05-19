import json
import os

import dataclasses_jsonschema
import pytest  # type: ignore

from hopeit.server.version import APPS_API_VERSION, ENGINE_VERSION
from hopeit.app.config import AppConfig, AppDescriptor, EventDescriptor, AppEngineConfig, \
    EventType, ReadStreamDescriptor, WriteStreamDescriptor, EventConfig, EventLoggingConfig
from hopeit.app.config import parse_app_config_json

APP_VERSION = APPS_API_VERSION.replace('.', "x")


@pytest.fixture
def valid_config_json() -> str:
    return """
{
  "app" : {
    "name": "simple_example",
    "version": "${HOPEIT_APPS_API_VERSION}"
  },
  "engine": {
    "import_modules": ["model"],
    "read_stream_timeout": 1,
    "track_headers" : ["request_id", "correlation_id"]
  },
  "env" : {
    "fs": {
      "data_path": "${TEST_TMP_FOLDER}/{auto}/",
      "app_description": "This is {app.name} version {app.version}",
      "recursive_replacement": "Data is in {env.fs.data_path}. {env.fs.app_description}"
    }
  },
  "events": {
    "query_something" : {
      "type": "GET"
    },
    "save_something" : {
      "type": "POST"
    },
    "streams.something_event" : {
      "type": "POST",
      "write_stream": {
        "name": "{auto}"
      }
    },
    "streams.process_events": {
      "type": "STREAM",
      "read_stream": {
        "name": "{events.streams.something_event.write_stream.name}",
        "consumer_group": "{auto}"
      },
      "config": {
        "logging": {
          "extra_fields": ["something_id", "path"]
        }
      }
    }
  }
}
"""


@pytest.fixture
def valid_result_app_config() -> AppConfig:
    return AppConfig(
        app=AppDescriptor(
            name="simple_example",
            version=APPS_API_VERSION
        ),
        engine=AppEngineConfig(
            import_modules=["model"],
            read_stream_timeout=1,
            track_headers=["request_id", "correlation_id"]
        ),
        env={
            "fs": {
                "data_path": f"/tmp/simple_example.{APP_VERSION}.fs.data_path/",
                "app_description": f"This is simple_example version {APPS_API_VERSION}",
                "recursive_replacement":
                    f"Data is in /tmp/simple_example.{APP_VERSION}.fs.data_path/. " +
                    f"This is simple_example version {APPS_API_VERSION}"
            }
        },
        events={
            "query_something": EventDescriptor(
                type=EventType.GET
            ),
            "save_something": EventDescriptor(
                type=EventType.POST
            ),
            "streams.something_event": EventDescriptor(
                type=EventType.POST,
                write_stream=WriteStreamDescriptor(
                    name=f'simple_example.{APP_VERSION}.streams.something_event'
                )
            ),
            "streams.process_events": EventDescriptor(
                type=EventType.STREAM,
                read_stream=ReadStreamDescriptor(
                    name=f'simple_example.{APP_VERSION}.streams.something_event',
                    consumer_group=f'simple_example.{APP_VERSION}.streams.process_events'
                ),
                config=EventConfig(
                    logging=EventLoggingConfig(
                        extra_fields=['something_id', 'path']
                    )
                )
            )
        }
    )


def _get_env_mock(var_name):
    if var_name == 'TEST_TMP_FOLDER':
        return "/tmp"
    elif var_name == "HOPEIT_ENGINE_VERSION":
        return ENGINE_VERSION
    elif var_name == "HOPEIT_APPS_API_VERSION":
        return APPS_API_VERSION
    raise RuntimeError(f"Missing mocked env {var_name}")


def test_parse_app_config_json(monkeypatch,
                               valid_config_json: str,
                               valid_result_app_config: AppConfig):
    monkeypatch.setattr(os, 'getenv', _get_env_mock)
    config = parse_app_config_json(valid_config_json)
    assert config == valid_result_app_config


def test_invalid_app_name(monkeypatch, valid_config_json: str):
    monkeypatch.setattr(os, 'getenv', _get_env_mock)
    config_json = _replace_in_config(valid_config_json, key='app.name', value='')
    with pytest.raises(ValueError):
        parse_app_config_json(config_json)


def test_invalid_app_version(monkeypatch, valid_config_json: str):
    monkeypatch.setattr(os, 'getenv', _get_env_mock)
    config_json = _replace_in_config(valid_config_json, key='app.version', value='')
    with pytest.raises(ValueError):
        parse_app_config_json(config_json)


def test_parse_invalid_event_type(monkeypatch, valid_config_json: str):
    monkeypatch.setattr(os, 'getenv', _get_env_mock)
    config_json = _replace_in_config(
        valid_config_json,
        key='events.query_something.type',
        value='INVALID'
    )
    with pytest.raises(dataclasses_jsonschema.ValidationError):
        parse_app_config_json(config_json)


def _replace_in_config(config_json: str, *, key: str, value: str) -> str:
    config_dict = json.loads(config_json)
    aux = config_dict
    for k in key.split('.'):
        if isinstance(aux[k], dict):
            aux = aux[k]
        else:
            aux[k] = value
    return json.dumps(config_dict)
