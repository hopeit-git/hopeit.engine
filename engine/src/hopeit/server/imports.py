"""
Utilities to import apps modules and datatypes at runtime / server start
"""
from importlib import import_module
from types import ModuleType

from hopeit.app.config import AppConfig
from hopeit.server.names import module_name

__all__ = ['find_event_handler']


def find_event_handler(*, app_config: AppConfig,
                       event_name: str) -> ModuleType:
    """
    Returns the initialized module implementing the event business logic.
    """
    imps = app_config.engine.import_modules \
        if app_config.engine and app_config.engine.import_modules \
        else [app_config.app.name]

    errors = []
    for imp in imps:
        try:
            qualified_name = module_name(imp, event_name)
            return import_module(qualified_name)
        except ImportError as e:
            errors.append(e)
    raise ImportError(f"Cannot import {event_name} from {imps}", *errors)
