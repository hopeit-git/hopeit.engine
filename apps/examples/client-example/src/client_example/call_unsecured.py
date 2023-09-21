"""
Client Example: Call Unsecured
--------------------------------------------------------------------
List all available Something objects connecting to simple-example app
"""
from typing import Optional, List

from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger
from hopeit.app.client import app_call_list
from hopeit.dataobjects import dataobject, dataclass

from model import Something


__steps__ = ["list_something"]

__api__ = event_api(
    summary="Client Example: Call Unsecured",
    query_args=[],
    responses={
        200: (List[Something], "List Something objects returned by simple-example call")
    },
)

logger, extra = app_extra_logger()


async def list_something(payload: None, context: EventContext) -> List[Something]:
    response: List[Something] = await app_call_list(
        "simple_example_conn_unsecured",
        event="list_somethings_unsecured",
        datatype=Something,
        payload=None,
        context=context
    )

    return response
