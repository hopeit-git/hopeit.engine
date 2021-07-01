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
from base64 import b64decode

from model import Something, SomethingParams
from client_example import CountAndSaveResult

__steps__ = ['count_objects', 'save_object']

__api__ = event_api(
    summary="Client Example: Count Objects and Save new one",
    query_args=[
        ('wildcard', Optional[str], "Wildcard to filter objects by name")
    ],
    responses={
        200: (CountAndSaveResult, "Count of Something objects returned by simple-example call")
    }
)

logger, extra = app_extra_logger()


async def count_objects(payload: None, context: EventContext, wildcard: str = '*') -> int:
    client = app_client("simple_example_conn", context)
    response = await client.call(
        "list_somethings", datatype=Something, payload=None, context=context, wildcard=wildcard
    )
    return len(response)


async def save_object(count: int, context: EventContext, wildcard: str = '*') -> int:
    client = app_client("simple_example_conn", context)
    user = b64decode(context.auth_info['payload'].encode()).decode().split(':', maxsplit=1)[0]
    params = SomethingParams(id=f"id{count}", user=user)
    saved = await client.call(
        "save_something", datatype=str, payload=params, context=context
    )
    return CountAndSaveResult(count=count, save_path=saved)
