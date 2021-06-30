"""
Client Example: Count Objects
--------------------------------------------------------------------
Count all available Something objects connecting to simple-example app
"""
from typing import Optional, List

from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger
from hopeit.app.client import app_client

from model import Something

__steps__ = ['load_all']

__api__ = event_api(
    summary="Client Example: Count Objects",
    query_args=[
        ('wildcard', Optional[str], "Wildcard to filter objects by name")
    ],
    responses={
        200: (int, "Count of Something objects returned by simple-example call")
    }
)

logger, extra = app_extra_logger()

async def load_all(payload: None, context: EventContext, wildcard: str = '*') -> int:
    client = app_client("simple-example-conn", context)
    response = await client.call(
        "list-somethings", datatype=Something, payload=None, context=context
    )
    return len(response)
