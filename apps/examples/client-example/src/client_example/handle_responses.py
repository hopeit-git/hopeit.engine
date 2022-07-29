"""
Client Example: Handle Responses
--------------------------------------------------------------------
Non default responses and UnhandledResponse exception

To manage different types of responses from the same endpoint we can use the `responses` parameter where we list the
http response status codes expected and the corresponding data type for each one. In this example `app_call` expect
and handle, 200 and 404 responses.

Also in the code you can see how to handle an expection of type `UnhandledResponse` and log as warining.
"""

from typing import Union
from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger
from hopeit.app.client import app_call, UnhandledResponse
from hopeit.dataobjects import dataobject, dataclass
from model import Something, SomethingNotFound

__steps__ = ['handle_exception', 'handle_responses']

__api__ = event_api(
    summary="Client Example: Handle Responses",
    query_args=[
        ('item_id', str, 'Item Id to read'),
        ('partition_key', str, 'Partition folder in `YYYY/MM/DD/HH` format')
    ],
    responses={
        200: (str, "Show the response of the call")
    }
)

logger, extra = app_extra_logger()


@dataobject
@dataclass
class ListOptions:
    item_id: str
    partition_key: str


async def handle_exception(payload: None, context: EventContext, item_id: str, partition_key: str) -> ListOptions:
    """
    To manage different types of responses from the same endpoint we can use the `responses` parameter where we list
    the http response status codes expected and the corresponding data type for each one. In this example app_call
    expect 200 and 202 responses but unexpectedly we will get 400, this is captured as `UnhandledResponse` exception
    and reported in the log.
    """
    responses = {200: Something, 404: str}
    try:
        await app_call(
            "simple_example_conn", event="query_something", datatype=Something, payload=None,
            context=context, responses=responses)
    except UnhandledResponse as e:
        logger.warning(
            context, f"Unexpected response status {e.status}")
    return ListOptions(item_id=item_id, partition_key=partition_key)


async def handle_responses(options: ListOptions, context: EventContext) -> str:
    """
    To manage different types of responses from the same endpoint we can use the `responses` parameter where we list
    the http response status codes expected and the corresponding data type for each one. In this example app_call
    expect 200 and 404 responses. This sample overwrite the `datatype` parameter for default 200 response with the
    listed in the `responses` parameter.
    """

    something: Union[Something, SomethingNotFound] = await app_call(
        "simple_example_conn", event="query_something", datatype=Something,
        payload=None, context=context,
        responses={404: SomethingNotFound},
        item_id=options.item_id, partition_key=options.partition_key)

    if isinstance(something, Something):
        return f"Got 200 response with: '{something}'"
    return f"Got 404 response with: '{something}'"
