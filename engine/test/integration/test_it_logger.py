import logging
import os
import socket
import pytest  # type: ignore

from hopeit.app.config import EventSettings, EventLoggingConfig
import hopeit.server.logger as server_logging
import hopeit.server.version as version
from hopeit.app.context import EventContext
from hopeit.server.config import AuthType
from hopeit.server.events import get_event_settings
from hopeit.server.logger import setup_app_logger
from hopeit.app.logger import app_logger, app_extra_logger

from mock_app import mock_event_logging as mock_event, mock_app_config  # type: ignore  # noqa: F401

FILE_BASE_PATH = '/tmp'


class MockHandler(logging.FileHandler):
    record: logging.LogRecord
    formatter: logging.Formatter

    def emit(self, record):
        MockHandler.record = record
        super().emit(record)

    @staticmethod
    def mock(logger_name, formatter, path=None):
        MockHandler.formatter = formatter
        MockHandler.record = None
        handler = MockHandler(f"{FILE_BASE_PATH}/{logger_name.replace(' ', '_')}.log")
        handler.setFormatter(formatter)
        return handler


def _event_context(mock_app_config):  # noqa: F811
    return EventContext(
        app_config=mock_app_config,
        plugin_config=mock_app_config,
        event_name='mock_event_logging',
        settings=get_event_settings(mock_app_config.effective_settings, 'mock_event_logging'),
        track_ids={
            'track.operation_id': 'test_operation_id',
            'track.request_id': 'test_request_id',
            'track.request_ts': '2020-01-01T00:00:00Z',
            'track.session_id': 'test_session_id'
        },
        auth_info={'auth_type': AuthType.UNSECURED, 'allowed': 'true'}
    )


def _get_app_logger(monkeypatch, mock_app_config):  # noqa: F811
    _patch_logger(monkeypatch)
    mock_event.logger = app_logger()
    settings = get_event_settings(mock_app_config.effective_settings, 'mock_event')
    setup_app_logger(mock_event,
                     app_config=mock_app_config,
                     name='mock_event',
                     event_settings=settings)
    return mock_event.logger


def _get_app_extra_logger(monkeypatch, mock_app_config):  # noqa: F811
    _patch_logger(monkeypatch)
    event_settings = EventSettings(
        logging=EventLoggingConfig(
            extra_fields=['field1', 'field2']
        )
    )
    mock_event.logger, mock_event.extra = app_extra_logger()
    setup_app_logger(mock_event,
                     app_config=mock_app_config,
                     name='mock_event',
                     event_settings=event_settings)
    return mock_event.logger, mock_event.extra


def _get_engine_logger(monkeypatch, mock_app_config):  # noqa: F811
    _patch_logger(monkeypatch)
    logger = server_logging.engine_logger()
    logger.init_server(mock_app_config.server)
    logger.init_app(mock_app_config, plugins=[])
    return logger


def _get_engine_extra_logger(monkeypatch, mock_app_config):  # noqa: F811
    _patch_logger(monkeypatch)
    logger, extra = server_logging.engine_extra_logger()
    logger.init_server(mock_app_config.server)
    logger.init_app(mock_app_config, plugins=[])
    return logger, extra


def _get_cli_logger(monkeypatch):  # noqa: F811
    _patch_logger(monkeypatch, '_console_handler')
    return server_logging.engine_logger().init_cli("test_cli_logger")


def _patch_logger(monkeypatch, handler_name: str = '_file_handler'):
    monkeypatch.setattr(os, 'getpid', lambda: "test_pid")
    monkeypatch.setattr(socket, 'gethostname', lambda: "test_host")
    monkeypatch.setattr(server_logging, handler_name, MockHandler.mock)


def test_get_app_logger(monkeypatch, mock_app_config):  # noqa: F811
    logger = _get_app_logger(monkeypatch, mock_app_config)
    logger.info(_event_context(mock_app_config), "Test message")
    assert MockHandler.formatter.format(MockHandler.record)[24:] \
        == "| INFO | mock_app test mock_event test_host test_pid | Test message " \
           "| track.operation_id=test_operation_id " \
           "| track.request_id=test_request_id | track.request_ts=2020-01-01T00:00:00Z " \
           "| track.session_id=test_session_id | event.app=mock_app.test"
    logger.warning(_event_context(mock_app_config), "Test message")
    assert MockHandler.formatter.format(MockHandler.record)[24:] \
        == "| WARNING | mock_app test mock_event test_host test_pid | Test message " \
           "| track.operation_id=test_operation_id " \
           "| track.request_id=test_request_id | track.request_ts=2020-01-01T00:00:00Z " \
           "| track.session_id=test_session_id | event.app=mock_app.test"
    logger.error(_event_context(mock_app_config), "Test message")
    assert MockHandler.formatter.format(MockHandler.record)[24:] \
        == "| ERROR | mock_app test mock_event test_host test_pid | Test message " \
           "| track.operation_id=test_operation_id " \
           "| track.request_id=test_request_id | track.request_ts=2020-01-01T00:00:00Z " \
           "| track.session_id=test_session_id | event.app=mock_app.test"


def test_app_logger_traceback(monkeypatch, mock_app_config):  # noqa: F811
    logger = _get_app_logger(monkeypatch, mock_app_config)
    exc = AssertionError("Test for error")
    logger.info(_event_context(mock_app_config), exc)
    assert MockHandler.formatter.format(MockHandler.record)[24:] \
        == "| INFO | mock_app test mock_event test_host test_pid | Test for error " \
           "| track.operation_id=test_operation_id " \
           "| track.request_id=test_request_id | track.request_ts=2020-01-01T00:00:00Z " \
           "| track.session_id=test_session_id | event.app=mock_app.test " \
           "| trace=%5B%22AssertionError%3A%20Test%20for%20error%5Cn%22%5D"
    logger.warning(_event_context(mock_app_config), exc)
    assert MockHandler.formatter.format(MockHandler.record)[24:] \
        == "| WARNING | mock_app test mock_event test_host test_pid | Test for error " \
           "| track.operation_id=test_operation_id " \
           "| track.request_id=test_request_id | track.request_ts=2020-01-01T00:00:00Z " \
           "| track.session_id=test_session_id | event.app=mock_app.test " \
           "| trace=%5B%22AssertionError%3A%20Test%20for%20error%5Cn%22%5D"
    logger.error(_event_context(mock_app_config), exc)
    assert MockHandler.formatter.format(MockHandler.record)[24:] \
        == "| ERROR | mock_app test mock_event test_host test_pid | Test for error " \
           "| track.operation_id=test_operation_id " \
           "| track.request_id=test_request_id | track.request_ts=2020-01-01T00:00:00Z " \
           "| track.session_id=test_session_id | event.app=mock_app.test " \
           "| trace=%5B%22AssertionError%3A%20Test%20for%20error%5Cn%22%5D"


def test_get_app_logger_extra(monkeypatch, mock_app_config):  # noqa: F811
    logger, extra = _get_app_extra_logger(monkeypatch, mock_app_config)
    context = _event_context(mock_app_config)
    logger.info(
        context,
        "Test message",
        extra=extra(field1='value1', field2=42, field3='optional')
    )
    assert MockHandler.formatter.format(MockHandler.record)[24:] \
        == "| INFO | mock_app test mock_event test_host test_pid | Test message " \
           "| extra.field1=value1 | extra.field2=42 | extra.field3=optional " \
           "| track.operation_id=test_operation_id " \
           "| track.request_id=test_request_id | track.request_ts=2020-01-01T00:00:00Z " \
           "| track.session_id=test_session_id | event.app=mock_app.test"

    logger.warning(
        context,
        "Test message",
        extra=extra(field1='value1', field2=42, field3='optional')
    )
    assert MockHandler.formatter.format(MockHandler.record)[24:] \
        == "| WARNING | mock_app test mock_event test_host test_pid " \
           "| Test message " \
           "| extra.field1=value1 | extra.field2=42 | extra.field3=optional " \
           "| track.operation_id=test_operation_id " \
           "| track.request_id=test_request_id | track.request_ts=2020-01-01T00:00:00Z " \
           "| track.session_id=test_session_id | event.app=mock_app.test"

    logger.error(
        context,
        "Test message",
        extra=extra(field1='value1', field2=42, field3='optional')
    )
    assert MockHandler.formatter.format(MockHandler.record)[24:] \
        == "| ERROR | mock_app test mock_event test_host test_pid | Test message " \
           "| extra.field1=value1 | extra.field2=42 | extra.field3=optional " \
           "| track.operation_id=test_operation_id " \
           "| track.request_id=test_request_id | track.request_ts=2020-01-01T00:00:00Z " \
           "| track.session_id=test_session_id | event.app=mock_app.test"

    with pytest.raises(KeyError):
        logger.info(context, "Missing required field", extra=extra(field3='optional'))


def test_engine_logger(monkeypatch, mock_app_config):  # noqa: F811
    logger = _get_engine_logger(monkeypatch, mock_app_config)
    context = _event_context(mock_app_config)

    logger.info(
        context, "Log message",
        extra=server_logging.extra_values([], field1='value1', field2=42)
    )
    assert MockHandler.formatter.format(MockHandler.record)[24:] \
        == "| INFO | mock_app test mock_event_logging test_host test_pid | Log message " \
           "| extra.field1=value1 | extra.field2=42 " \
           "| track.operation_id=test_operation_id " \
           "| track.request_id=test_request_id | track.request_ts=2020-01-01T00:00:00Z " \
           "| track.session_id=test_session_id | event.app=mock_app.test"

    logger.warning(
        context, "Log message",
        extra=server_logging.extra_values([], field1='value1', field2=42)
    )
    assert MockHandler.formatter.format(MockHandler.record)[24:] \
        == "| WARNING | mock_app test mock_event_logging test_host test_pid | Log message " \
           "| extra.field1=value1 | extra.field2=42 " \
           "| track.operation_id=test_operation_id " \
           "| track.request_id=test_request_id | track.request_ts=2020-01-01T00:00:00Z " \
           "| track.session_id=test_session_id | event.app=mock_app.test"

    logger.error(
        context, "Log message",
        extra=server_logging.extra_values([], field1='value1', field2=42)
    )
    assert MockHandler.formatter.format(MockHandler.record)[24:] \
        == "| ERROR | mock_app test mock_event_logging test_host test_pid | Log message " \
           "| extra.field1=value1 | extra.field2=42 " \
           "| track.operation_id=test_operation_id " \
           "| track.request_id=test_request_id | track.request_ts=2020-01-01T00:00:00Z " \
           "| track.session_id=test_session_id | event.app=mock_app.test"

    logger.start(
        context,
        extra=server_logging.extra_values([], field1='value1', field2=42)
    )
    assert MockHandler.formatter.format(MockHandler.record)[24:] \
        == "| INFO | mock_app test mock_event_logging test_host test_pid | START " \
           "| extra.field1=value1 | extra.field2=42 " \
           "| track.operation_id=test_operation_id " \
           "| track.request_id=test_request_id | track.request_ts=2020-01-01T00:00:00Z " \
           "| track.session_id=test_session_id | event.app=mock_app.test"

    logger.done(
        context,
        extra=server_logging.combined(
            server_logging.extra_values([], field1='value1', field2=42)
        )
    )
    assert MockHandler.formatter.format(MockHandler.record)[24:] \
        == "| INFO | mock_app test mock_event_logging test_host test_pid | DONE " \
           "| extra.field1=value1 | extra.field2=42 " \
           "| track.operation_id=test_operation_id " \
           "| track.request_id=test_request_id | track.request_ts=2020-01-01T00:00:00Z " \
           "| track.session_id=test_session_id | event.app=mock_app.test"

    logger.ignored(
        context,
        extra=server_logging.combined(
            server_logging.extra_values([], field1='value1', field2=42)
        )
    )
    assert MockHandler.formatter.format(MockHandler.record)[24:] \
        == "| WARNING | mock_app test mock_event_logging test_host test_pid | IGNORED " \
           "| extra.field1=value1 | extra.field2=42 " \
           "| track.operation_id=test_operation_id " \
           "| track.request_id=test_request_id | track.request_ts=2020-01-01T00:00:00Z " \
           "| track.session_id=test_session_id | event.app=mock_app.test"

    logger.failed(
        context,
        extra=server_logging.combined(
            server_logging.extra_values([], field1='value1', field2=42)
        )
    )
    assert MockHandler.formatter.format(MockHandler.record)[24:] \
        == "| ERROR | mock_app test mock_event_logging test_host test_pid | FAILED " \
           "| extra.field1=value1 | extra.field2=42 " \
           "| track.operation_id=test_operation_id " \
           "| track.request_id=test_request_id | track.request_ts=2020-01-01T00:00:00Z " \
           "| track.session_id=test_session_id | event.app=mock_app.test"


def test_engine_logger_no_context(monkeypatch, mock_app_config):  # noqa: F811
    logger = _get_engine_logger(monkeypatch, mock_app_config)

    logger.info(
        "test_it_logging", "Log message",
        extra=server_logging.extra_values([], field1='value1', field2=42)
    )
    assert MockHandler.formatter.format(MockHandler.record)[24:] \
        == f"| INFO | {version.ENGINE_NAME} {version.ENGINE_VERSION} engine test_host test_pid " \
           "| [test_it_logging] Log message " \
           "| extra.field1=value1 | extra.field2=42"

    logger.warning(
        "test_it_logging", "Log message",
        extra=server_logging.extra_values([], field1='value1', field2=42)
    )
    assert MockHandler.formatter.format(MockHandler.record)[24:] \
        == "| WARNING " \
           f"| {version.ENGINE_NAME} {version.ENGINE_VERSION} engine test_host test_pid " \
           "| [test_it_logging] Log message " \
           "| extra.field1=value1 | extra.field2=42"

    logger.error(
        "test_it_logging", "Log message",
        extra=server_logging.extra_values([], field1='value1', field2=42)
    )
    assert MockHandler.formatter.format(MockHandler.record)[24:] \
        == f"| ERROR | {version.ENGINE_NAME} {version.ENGINE_VERSION} engine test_host test_pid " \
           "| [test_it_logging] Log message " \
           "| extra.field1=value1 | extra.field2=42"


def test_engine_logger_traceback(monkeypatch, mock_app_config):  # noqa: F811
    logger = _get_engine_logger(monkeypatch, mock_app_config)

    exc = AssertionError("Test for error")
    logger.info(
        "test_it_logging", exc,
        extra=server_logging.extra_values([], field1='value1', field2=42)
    )
    assert MockHandler.formatter.format(MockHandler.record)[24:] \
        == f"| INFO | {version.ENGINE_NAME} {version.ENGINE_VERSION} engine test_host test_pid " \
           "| [test_it_logging] Test for error " \
           "| extra.field1=value1 | extra.field2=42 " \
           "| trace=%5B%22AssertionError%3A%20Test%20for%20error%5Cn%22%5D"

    logger.warning(
        "test_it_logging", exc,
        extra=server_logging.extra_values([], field1='value1', field2=42)
    )
    assert MockHandler.formatter.format(MockHandler.record)[24:] \
        == "| WARNING " \
           f"| {version.ENGINE_NAME} {version.ENGINE_VERSION} engine test_host test_pid " \
           "| [test_it_logging] Test for error " \
           "| extra.field1=value1 | extra.field2=42 " \
           "| trace=%5B%22AssertionError%3A%20Test%20for%20error%5Cn%22%5D"

    logger.error(
        "test_it_logging", exc,
        extra=server_logging.extra_values([], field1='value1', field2=42)
    )
    assert MockHandler.formatter.format(MockHandler.record)[24:] \
        == f"| ERROR | {version.ENGINE_NAME} {version.ENGINE_VERSION} engine test_host test_pid " \
           "| [test_it_logging] Test for error " \
           "| extra.field1=value1 | extra.field2=42 " \
           "| trace=%5B%22AssertionError%3A%20Test%20for%20error%5Cn%22%5D"


def test_engine_extra_logger(monkeypatch, mock_app_config):  # noqa: F811
    logger, extra = _get_engine_extra_logger(monkeypatch, mock_app_config)
    context = _event_context(mock_app_config)

    logger.info(
        context, "Log message",
        extra=extra(field1='value1', field2=42)
    )
    assert MockHandler.formatter.format(MockHandler.record)[24:] \
        == "| INFO | mock_app test mock_event_logging test_host test_pid | Log message " \
           "| extra.field1=value1 | extra.field2=42 " \
           "| track.operation_id=test_operation_id " \
           "| track.request_id=test_request_id | track.request_ts=2020-01-01T00:00:00Z " \
           "| track.session_id=test_session_id | event.app=mock_app.test"

    logger.warning(
        context, "Log message",
        extra=extra(field1='value1', field2=42)
    )
    assert MockHandler.formatter.format(MockHandler.record)[24:] \
        == "| WARNING | mock_app test mock_event_logging test_host test_pid | Log message " \
           "| extra.field1=value1 | extra.field2=42 " \
           "| track.operation_id=test_operation_id " \
           "| track.request_id=test_request_id | track.request_ts=2020-01-01T00:00:00Z " \
           "| track.session_id=test_session_id | event.app=mock_app.test"

    logger.error(
        context, "Log message",
        extra=extra(field1='value1', field2=42)
    )
    assert MockHandler.formatter.format(MockHandler.record)[24:] \
        == "| ERROR | mock_app test mock_event_logging test_host test_pid | Log message " \
           "| extra.field1=value1 | extra.field2=42 " \
           "| track.operation_id=test_operation_id " \
           "| track.request_id=test_request_id | track.request_ts=2020-01-01T00:00:00Z " \
           "| track.session_id=test_session_id | event.app=mock_app.test"

    logger.start(
        context,
        extra=extra(field1='value1', field2=42)
    )
    assert MockHandler.formatter.format(MockHandler.record)[24:] \
        == "| INFO | mock_app test mock_event_logging test_host test_pid | START " \
           "| extra.field1=value1 | extra.field2=42 " \
           "| track.operation_id=test_operation_id " \
           "| track.request_id=test_request_id | track.request_ts=2020-01-01T00:00:00Z " \
           "| track.session_id=test_session_id | event.app=mock_app.test"

    logger.done(
        context,
        extra=server_logging.combined(
            extra(field1='value1', field2=42)
        )
    )
    assert MockHandler.formatter.format(MockHandler.record)[24:] \
        == "| INFO | mock_app test mock_event_logging test_host test_pid | DONE " \
           "| extra.field1=value1 | extra.field2=42 " \
           "| track.operation_id=test_operation_id " \
           "| track.request_id=test_request_id | track.request_ts=2020-01-01T00:00:00Z " \
           "| track.session_id=test_session_id | event.app=mock_app.test"

    logger.ignored(
        context,
        extra=server_logging.combined(
            extra(field1='value1', field2=42)
        )
    )
    assert MockHandler.formatter.format(MockHandler.record)[24:] \
        == "| WARNING | mock_app test mock_event_logging test_host test_pid | IGNORED " \
           "| extra.field1=value1 | extra.field2=42 " \
           "| track.operation_id=test_operation_id " \
           "| track.request_id=test_request_id | track.request_ts=2020-01-01T00:00:00Z " \
           "| track.session_id=test_session_id | event.app=mock_app.test"

    logger.failed(
        context,
        extra=server_logging.combined(
            server_logging.extra_values([], field1='value1', field2=42)
        )
    )
    assert MockHandler.formatter.format(MockHandler.record)[24:] \
        == "| ERROR | mock_app test mock_event_logging test_host test_pid | FAILED " \
           "| extra.field1=value1 | extra.field2=42 " \
           "| track.operation_id=test_operation_id " \
           "| track.request_id=test_request_id | track.request_ts=2020-01-01T00:00:00Z " \
           "| track.session_id=test_session_id | event.app=mock_app.test"


def test_cli_logger(monkeypatch):  # noqa: F811
    logger = _get_cli_logger(monkeypatch)

    logger.info(
        "test_cli_logger", "Log message",
        extra=server_logging.extra_values([], field1='value1', field2=42)
    )
    assert MockHandler.formatter.format(MockHandler.record)[24:] \
        == f"| INFO | hopeit.engine {version.ENGINE_VERSION} test_cli_logger test_host test_pid " \
           "| [test_cli_logger] Log message | extra.field1=value1 | extra.field2=42"

    logger.warning(
        "test_cli_logger", "Log message",
        extra=server_logging.extra_values([], field1='value1', field2=42)
    )
    assert MockHandler.formatter.format(MockHandler.record)[24:] \
        == f"| WARNING | hopeit.engine {version.ENGINE_VERSION} test_cli_logger test_host test_pid " \
           "| [test_cli_logger] Log message | extra.field1=value1 | extra.field2=42"

    logger.error(
        "test_cli_logger", "Log message",
        extra=server_logging.extra_values([], field1='value1', field2=42)
    )
    assert MockHandler.formatter.format(MockHandler.record)[24:] \
        == f"| ERROR | hopeit.engine {version.ENGINE_VERSION} test_cli_logger test_host test_pid " \
           "| [test_cli_logger] Log message | extra.field1=value1 | extra.field2=42"
