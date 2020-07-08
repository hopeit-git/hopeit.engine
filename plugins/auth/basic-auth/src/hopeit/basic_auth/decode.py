"""
Basic Auth: Decode
--------------------------------------------------------------------
Returns decoded auth info
"""
from hopeit.app.api import event_api
from hopeit.basic_auth import ContextUserInfo
from hopeit.app.context import EventContext
from hopeit.app.logger import app_logger

logger = app_logger()

__steps__ = ['decode']

__api__ = event_api(
    responses={
        200: (ContextUserInfo, "Information extracted from token")
    }
)


async def decode(payload: None, context: EventContext) -> ContextUserInfo:
    token_info = context.auth_info['payload']
    return ContextUserInfo(
        id=token_info['id'],
        user=token_info['user'],
        email=token_info['email']
    )
