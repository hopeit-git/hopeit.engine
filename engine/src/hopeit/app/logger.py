"""
Helpers to provide uniform logging to engine and apps
"""
import logging
from functools import partial
from typing import Tuple, Callable

from hopeit.server.logger import extra_values

__all__ = ['app_logger',
           'app_extra_logger']

DEFAULT_APP_LOGGER = 'app_logger_default'


def app_logger() -> logging.Logger:
    """
    Returns a placeholder to allow engine to setup later proper logger
    Allows to reference `logger` as a module variable.

    Use at module level in events implementation::

        from hopeit.logger import app_logger()

        logger = app_logger()

    """
    return logging.getLogger(DEFAULT_APP_LOGGER)


def app_extra_logger() -> Tuple[logging.Logger, Callable]:
    """
    Returns a placeholder to allow engine to setup later proper logger
    Allows to reference `logger` as a module variable,
    and the function `extra` to send extra values to logger.


    Use at module level in events implementation::

     from hopeit.logger import app_extra_logger()

     logger, extra = app_extra_logger()

    """
    return logging.getLogger(DEFAULT_APP_LOGGER), partial(extra_values, [])
