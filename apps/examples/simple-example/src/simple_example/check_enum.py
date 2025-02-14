"""
Simple Example: Check enum values
--------------------------------------------------------------------
Check enum values used in api schema
"""

from enum import Enum
from typing import Optional

from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger
from hopeit.dataobjects import dataobject, dataclass

__steps__ = ["check_value"]


class CustomValue(str, Enum):
    VALUE1 = "value1"
    VALUE2 = "value2"
    VALUE3 = "value3"


@dataobject
@dataclass
class CheckEnumResponse:
    value: CustomValue




__api__ = event_api(
    summary="Simple Example: Check enum values",
    query_args=[
        (
            "enum_value",
            CustomValue,
            "Enum value to validate"
        )
    ],
    responses={
        200: (list[CheckEnumResponse], "Enum value"),
    },
)

logger, extra = app_extra_logger()


async def check_value(payload: None, context: EventContext, enum_value: str) -> list[CheckEnumResponse]:
    """
    Check enum_value:str query arg is a valid CustomValue enum value and return it,
    return None if it is not a valid value
    """
    try:
        instance = CustomValue(enum_value)
    except ValueError:
        return []
    return [CheckEnumResponse(value=instance)]
