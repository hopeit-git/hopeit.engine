"""
Adapter for pydantic mypy plugin to recognize @dataobject annotation
"""
from typing import Callable, Optional, Type as TypingType
from mypy.plugin import (
    ClassDefContext,
    Plugin,
)
from pydantic.mypy import PydanticPlugin

DATACLASS_FULLNAME = 'hopeit.dataobjects.dataobject'


def plugin(version: str) -> 'TypingType[Plugin]':
    return DataObjectPlugin


class DataObjectPlugin(PydanticPlugin):

    def get_class_decorator_hook(self, fullname: str) -> Optional[Callable[[ClassDefContext], None]]:
        if fullname == DATACLASS_FULLNAME:
            return self._pydantic_model_class_maker_callback
        return None
