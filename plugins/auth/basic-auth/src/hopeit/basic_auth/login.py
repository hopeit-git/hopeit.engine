"""
Basic Auth: Login
--------------------------------------------------------------------
Handles users login using basic-auth
and generate access tokens for external services invoking apps
plugged in with basic-auth plugin.
"""
from datetime import datetime, timezone
import base64

from hopeit.app.api import event_api
from hopeit.basic_auth import ContextUserInfo, AuthInfo, AuthInfoExtended, authorize, set_refresh_token
from hopeit.app.context import EventContext, PostprocessHook
from hopeit.app.logger import app_logger
from hopeit.toolkit.auth import AuthType
from hopeit.app.errors import Unauthorized

logger = app_logger()

__steps__ = ['login']

__api__ = event_api(
    responses={
        200: (AuthInfo, "Authentication information to be used for further API calls"),
        401: (Unauthorized.ErrorInfo, "Login failed, invalid credentials")
    }
)


async def login(payload: None, context: EventContext) -> AuthInfoExtended:
    """
    Returns a new access and refresh token for a set of given basic-auth credentials
    """
    assert context.auth_info['allowed']
    now = datetime.now().astimezone(timezone.utc)
    if context.auth_info['auth_type'] == AuthType.BASIC:
        data = base64.b64decode(context.auth_info['payload'].encode()).decode()
        user_info = ContextUserInfo(
            id='id',
            user=data.split(":")[0],  # TODO: Check password!!
            email='test@email'
        )
        return authorize(context, user_info, now)
    raise Unauthorized('Invalid authorization')


async def __postprocess__(payload: AuthInfoExtended,
                          context: EventContext, *,
                          response: PostprocessHook) -> AuthInfo:
    set_refresh_token(context.app, context.auth_info, payload, response)
    return payload.to_auth_info()
