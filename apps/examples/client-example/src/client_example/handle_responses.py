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
from hopeit.basic_auth import AuthInfo
from hopeit.dataobjects import dataobject, dataclass
from hopeit.toolkit import auth
from hopeit.server.web import Unauthorized
from model import Something, SomethingNotFound

__steps__ = ['ensure_login', 'handle_exception', 'handle_respones']

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


async def ensure_login(payload: None, context: EventContext, item_id: str, partition_key: str) -> ListOptions:
    """
    Using Basic auth credentials in context attempts login to server side app and validates
    login response comes from attempted source using public keys. Then, the following steps
    will execute using the client Bearer token.

    This example shows how to ensure both client and server apps can trust each other by having
    installed the counterpart's public key on their running environments.
    """
    auth_response = await app_call(
        "simple_example_auth_conn",
        event="login", datatype=AuthInfo, payload=None, context=context
    )
    auth_info = auth.validate_token(auth_response.access_token, context)
    if auth_info is None:
        raise Unauthorized("Client app does not recognize server login response (using public key)")
    logger.info(context, "Logged in to app", extra=extra(app=auth_info['app'], user=auth_info['user']))
    return ListOptions(item_id=item_id, partition_key=partition_key)


async def handle_exception(options: ListOptions, context: EventContext) -> ListOptions:
    """
    To manage different types of responses from the same endpoint we can use the `responses` parameter where we list
    the http response status codes expected and the corresponding data type for each one. In this example app_call
    expect 200 and 202 responses but unexpectedly we will get 400, this is captured as `UnhandledResponse` exception
    and reported in the log.
    """
    responses = {200: Something, 404: str}
    try:
        ret: Union[Something, SomethingNotFound] = await app_call(
            "simple_example_conn", event="query_something", datatype=Something, payload=None,
            context=context, responses=responses)
        if isinstance(ret, Something):
            logger.info(context, "Answer status 200")
        logger.info(context, "Answer status 404")
    except UnhandledResponse as e:
        logger.warning(
            context, f"Unexpected response status {e.status}")
    return options


async def handle_respones(options: ListOptions, context: EventContext) -> str:
    """
    To manage different types of responses from the same endpoint we can use the `responses` parameter where we list
    the http response status codes expected and the corresponding data type for each one. In this example app_call
    expect 200 and 404 responses. This sample overwrite the `datatype` parameter for default 200 response with the
    listed in the `responses` parameter.
    """

    something: Union[Something, SomethingNotFound] = await app_call(
        "simple_example_conn", event="query_something", datatype=Something,
        payload=None, context=context,
        responses={200: Something, 404: SomethingNotFound},
        item_id=options.item_id, partition_key=options.partition_key)

    if isinstance(something, Something):
        return f"You get a 200 response with: '{something}'"
    return f"You get a 404 response with: '{something}'"
