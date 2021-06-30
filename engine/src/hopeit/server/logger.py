"""
Server/Engine logging module
"""
import logging
import os
import socket
import time
from datetime import datetime
from functools import partial
from logging.handlers import WatchedFileHandler
from typing import Dict, Iterable, Union, List, Tuple, Callable, Any
from stringcase import snakecase  # type: ignore

from hopeit.server import version
from hopeit.app.config import EventDescriptor, AppDescriptor, AppConfig
from hopeit.app.context import EventContext
from hopeit.server.errors import json_exc
from hopeit.server.config import ServerConfig, LoggingConfig

DEFAULT_ENGINE_LOGGER = 'engine_logger_default'
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s | %(extra)s"
WARNINGS_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s | "

__all__ = ['extra_values',
           'combined',
           'setup_app_logger',
           'engine_logger',
           'extra_logger',
           'format_extra_values',
           'EngineLoggerWrapper']


class EventLoggerWrapper:
    """
    Wraps standard python logger to include request_id on every entry.
    """

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def debug(self, msg, *args, **kwargs) -> None:
        self.logger.debug(msg, *args, **kwargs)

    def info(self, context: EventContext, msg, *args, **kwargs) -> None:
        _enrich_extra(kwargs, context, msg)
        self.logger.info(msg, *args, **kwargs)

    def warning(self, context: EventContext, msg, *args, **kwargs) -> None:
        _enrich_extra(kwargs, context, msg)
        self.logger.warning(msg, *args, **kwargs)

    def error(self, context: EventContext, msg, *args, **kwargs) -> None:
        _enrich_extra(kwargs, context, msg)
        self.logger.error(msg, *args, **kwargs)


def _logger_name(app: AppDescriptor, name: str):
    host = socket.gethostname()
    pid = os.getpid()
    base_name = name.split('$')[0]
    return f"{app.name} {app.version} {base_name} {host} {pid}"


def _engine_logger_name(name: str):
    host = socket.gethostname()
    pid = os.getpid()
    return f"{version.ENGINE_NAME} {version.ENGINE_VERSION} {name} {host} {pid}"


def extra_values(required_fields: Iterable[str], *, prefix='extra.', **kwargs) -> Dict[str, str]:
    values = {
        **{k: kwargs[k] for k in required_fields},
        **kwargs
    }
    return {'extra': format_extra_values(values, prefix=prefix)}


def extra_logger():
    return partial(extra_values, [])


def combined(*args) -> Dict[str, str]:
    return {'extra': ' | '.join(x['extra'] for x in args)}


def format_extra_values(values: Dict[str, Any], prefix: str = '') -> str:
    return ' | '.join(
        f"{prefix}{k}={_format_value(v)}" for k, v in values.items()
    )


def _format_value(v: Any) -> str:
    if isinstance(v, float):
        return f"{v:.3f}"
    if isinstance(v, datetime):
        return v.isoformat()
    return str(v)


def _enrich_extra(logger_kwargs, context: Union[str, EventContext], msg=None):
    logger_kwargs['extra'] = logger_kwargs.get('extra', {'extra': ''})
    if isinstance(context, EventContext):
        logger_kwargs['extra']['extra'] += f" | {format_extra_values(context.track_ids)}"
    if isinstance(msg, Exception):
        logger_kwargs['extra']['extra'] += \
            f" | trace={json_exc(msg)}"
    logger_kwargs['extra']['extra'] = logger_kwargs['extra']['extra'].lstrip('| ')


def setup_extra_fields_extractor(module, *, event_info: EventDescriptor = None):
    if event_info and event_info.config and event_info.config.logging:
        extra_fields = event_info.config.logging.extra_fields
        module.extra = partial(extra_values, extra_fields)
    else:
        module.extra = partial(extra_values, [])


def _file_handler(logger_name: str, formatter: logging.Formatter, log_path: str):
    os.makedirs(log_path, exist_ok=True)
    path = f"{log_path}{snakecase(logger_name.replace('.', 'x'))}.log"
    file_handler = WatchedFileHandler(path)
    file_handler.setFormatter(formatter)
    return file_handler


def _console_handler(logger_name: str, formatter: logging.Formatter):
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    return ch


def _setup_standard_logger(logger_name: str, config: LoggingConfig, log_format: str = LOG_FORMAT) -> logging.Logger:
    """
    Creates a python logger using server logging configuration.
    By default all loggers are created with a file handler.
    If log_leve is DEBUG, an additional console handler is attached.

    :param logger_name: logger name
    :param config: server logging config
    :param log_format: format string, default to LOG_FORMAT
    :return: python standard logger
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(config.log_level)
    formatter = logging.Formatter(log_format)
    formatter.converter = time.gmtime  # type: ignore
    file_handler = _file_handler(logger_name, formatter, config.log_path)
    logger.addHandler(file_handler)
    if config.log_level == "DEBUG":
        ch = _console_handler(logger_name, formatter)
        logger.addHandler(ch)
    return logger


def _setup_console_logger(logger_name: str) -> logging.Logger:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(LOG_FORMAT)
    formatter.converter = time.gmtime  # type: ignore
    ch = _console_handler(logger_name, formatter)
    logger.addHandler(ch)
    return logger


class EngineLoggerWrapper:
    """
    Wrapper around standard python Logger to be used in engine modules.
    Provides additional functionallity to log extra info and metrics.
    """
    engine_logger: logging.Logger = logging.getLogger("bootstrap")
    loggers: Dict[str, logging.Logger] = {}

    def init_cli(self, name: str):
        EngineLoggerWrapper.engine_logger = _setup_console_logger(_engine_logger_name(name))
        return self

    def init_server(self, server_config: ServerConfig):
        _setup_standard_logger("py.warnings", config=server_config.logging, log_format=WARNINGS_LOG_FORMAT)
        logging.captureWarnings(True)
        EngineLoggerWrapper.engine_logger = _setup_standard_logger(
            _engine_logger_name("engine"), config=server_config.logging)
        return self

    def init_app(self, app_config: AppConfig, plugins: List[AppConfig]):
        """
        Initializes logger for an app and its plugins
        """
        assert app_config.server
        events = [
            *app_config.events.keys(),
            *[k for plugin in plugins for k in plugin.events.keys()]
        ]
        for event_name in events:
            logger_name = _logger_name(app_config.app, event_name)
            if logger_name not in self.loggers:
                logger = _setup_standard_logger(
                    logger_name, config=app_config.server.logging)
                self.loggers[logger_name] = logger
        return self

    def _logger(self, context: EventContext):
        logger_name = _logger_name(context.app, context.event_name)
        return self.loggers[logger_name]

    def start(self, context: EventContext, *args, **kwargs) -> None:
        self.info(context, 'START', *args, **kwargs)

    def failed(self, context: EventContext, *args, **kwargs) -> None:
        self.error(context, 'FAILED', *args, **kwargs)

    def ignored(self, context: EventContext, *args, **kwargs) -> None:
        self.warning(context, 'IGNORED', *args, **kwargs)

    def done(self, context: EventContext, *args, **kwargs) -> None:
        self.info(context, 'DONE', *args, **kwargs)

    def stats(self, context: EventContext, *args, **kwargs) -> None:
        self.info(context, 'STATS', *args, **kwargs)

    def debug(self, context: Union[str, EventContext], msg, *args, **kwargs) -> None:
        _enrich_extra(kwargs, context, msg)  # type: ignore
        if isinstance(context, str):
            self.engine_logger.debug(f"[{context}] {msg}", *args, **kwargs)
        else:
            self._logger(context).debug(msg, *args, **kwargs)  # type: ignore

    def info(self, context: Union[str, EventContext], msg, *args, **kwargs) -> None:
        _enrich_extra(kwargs, context, msg)  # type: ignore
        if isinstance(context, str):
            self.engine_logger.info(f"[{context}] {msg}", *args, **kwargs)
        else:
            self._logger(context).info(msg, *args, **kwargs)   # type: ignore

    def warning(self, context: Union[str, EventContext], msg, *args, **kwargs) -> None:
        _enrich_extra(kwargs, context, msg)  # type: ignore
        if isinstance(context, str):
            self.engine_logger.warning(f"[{context}] {msg}", *args, **kwargs)
        else:
            self._logger(context).warning(msg, *args, **kwargs)  # type: ignore

    def error(self, context: Union[str, EventContext], msg, *args, **kwargs) -> None:
        _enrich_extra(kwargs, context, msg)  # type: ignore
        if isinstance(context, str):
            self.engine_logger.error(f"[{context}] {msg}", *args, **kwargs)
        else:
            self._logger(context).error(msg, *args, **kwargs)  # type: ignore


def setup_app_logger(module, *, app_config: AppConfig, name: str, event_info: EventDescriptor):
    """
    Returns wrapper over python logging Logger for a given app and name.
    Logger name is made combining {app.name} {app.version} {name} {host} {pid}
    Standard fields to be logged are `%(asctime)s | %(levelname)s | %(name)s | %(message)s | `
    Specific apps can require for extra fields per event, configurabe in EventDescriptor
    """
    if hasattr(module, 'logger') and not isinstance(module.logger, EventLoggerWrapper):
        assert app_config.server
        logger_name = _logger_name(app_config.app, name)
        logger = EngineLoggerWrapper.loggers.get(logger_name)
        if logger is None:
            logger = _setup_standard_logger(logger_name, config=app_config.server.logging)
            EngineLoggerWrapper.loggers[logger_name] = logger
        module.logger = EventLoggerWrapper(logger)
        setup_extra_fields_extractor(module, event_info=event_info)


def engine_logger() -> EngineLoggerWrapper:
    """
    Returns logger wrapper for engine modules
    Allows to reference `logger` at module scope.

    Use at module level in events implementation::
    ```
        from hopeit.logger import engine_logger()

        logger = engine_logger()
    ```
    """
    return EngineLoggerWrapper()


def engine_extra_logger() -> Tuple[EngineLoggerWrapper, Callable]:
    """
    Returns logger wrapper for engine modules
    and a convenience function to submit extra values when logging.
    Allows to reference `logger` and `extra` at module scope.

    Use at module level in events implementation::
    ```
        from hopeit.logger import engine_logger()

        logger, extra = engine_extra_logger()

        ...

        logger.info(context, "message" extra=extra(value1="extra_value", ...))
    ```
    """
    return EngineLoggerWrapper(), partial(extra_values, [])
