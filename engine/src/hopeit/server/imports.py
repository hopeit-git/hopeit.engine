"""
Utilities to import apps modules and datatypes at runtime / server start
"""

from importlib import import_module
from types import ModuleType
from typing import Type

from hopeit.app.config import AppConfig, EventDescriptor
from hopeit.server.names import module_name

from hopeit.dataobjects import DataObject

__all__ = ["find_event_handler"]


def find_event_handler(
    *, app_config: AppConfig, event_name: str, event_info: EventDescriptor
) -> ModuleType:
    """
    Returns the initialized module implementing the event business logic.
    """
    if event_info.impl:
        return import_module(event_info.impl)

    imps = (
        app_config.engine.import_modules
        if app_config.engine and app_config.engine.import_modules
        else [app_config.app.name]
    )

    errors = []
    for imp in imps:
        try:
            qualified_name = module_name(imp, event_name)
            return import_module(qualified_name)
        except ImportError as e:
            errors.append(e)
    raise ImportError(f"Cannot import {event_name} from {imps}", *errors)


def find_datobject_type(qual_type_name: str) -> Type[DataObject]:
    mod_name, type_name = (
        ".".join(qual_type_name.split(".")[:-1]),
        qual_type_name.split(".")[-1],
    )
    module = import_module(mod_name)
    datatype = getattr(module, type_name)
    assert hasattr(
        datatype, "__data_object__"
    ), f"Type {qual_type_name} must be annotated with `@dataobject`."
    return datatype
