"""
Client Example: Count Objects
--------------------------------------------------------------------
Count all available Something objects connecting to simple-example app
"""
from typing import Optional, List
from base64 import b64decode

from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger
from hopeit.app.client import app_call, app_call_list
from hopeit.basic_auth import AuthInfo
from hopeit.dataobjects import dataobject, dataclass
from hopeit.toolkit import auth
from hopeit.server.web import Unauthorized

from model import Something, SomethingParams
from client_example import CountAndSaveResult

__steps__ = ['ensure_login', 'count_objects', 'save_object']

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


@dataobject
@dataclass
class ListOptions:
    wildcard: str


async def ensure_login(payload: None, context: EventContext, wildcard: str = '*') -> ListOptions:
    """
    Using Basic auth credentials in context attempts login to server side app and validates
    login response comes from attempted source using public keys. Then, the following steps
    will execute using the client Bearer token.

    This example shows how to ensure both client and server apps can trust each other by having
    installed their counterparts public keys on their running environments.
    """
    auth_response = await app_call(
        "simple_example_auth_conn",
        event="login", datatype=AuthInfo, payload=None, context=context
    )
    auth_info = auth.validate_token(auth_response.access_token, context)
    if auth_info is None:
        raise Unauthorized("Client app does not recognize server login response (using public key)")
    logger.info(context, "Logged in to app", extra=extra(app=auth_info['app'], user=auth_info['user']))
    return ListOptions(wildcard=wildcard)


async def count_objects(options: ListOptions, context: EventContext) -> int:
    response: List[Something] = await app_call_list(
        "simple_example_conn",
        event="list_somethings", datatype=Something,
        payload=None, context=context, wildcard=options.wildcard
    )
    return len(response)


async def save_object(count: int, context: EventContext, wildcard: str = '*') -> CountAndSaveResult:
    user = b64decode(context.auth_info['payload'].encode()).decode().split(':', maxsplit=1)[0]
    params = SomethingParams(id=f"id{count}", user=user)
    saved: str = await app_call(
        "simple_example_conn",
        event="save_something", datatype=str,
        payload=params, context=context
    )
    return CountAndSaveResult(count=count, save_path=saved)
