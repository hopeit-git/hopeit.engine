"""
Basic Auth: Logout
---------------------------------------------
Invalidates previous refresh cookies.
"""
from hopeit.app.api import event_api, app_base_route_name
from hopeit.app.context import EventContext, PostprocessHook
from hopeit.app.logger import app_logger
from hopeit.toolkit.auth import AuthType
from hopeit.app.errors import Unauthorized

logger = app_logger()

__steps__ = ['logout']

__api__ = event_api(
    summary="Basic Auth: Logout",
    responses={
        200: (str, "Logged out message."),
        401: (Unauthorized.ErrorInfo, "Login failed, invalid credentials or not logged in.")
    }
)


async def logout(payload: None, context: EventContext):
    assert context.auth_info['allowed']
    if not context.auth_info['auth_type'] == AuthType.REFRESH:
        raise Unauthorized('Invalid authorization')


async def __postprocess__(payload: None, context: EventContext, *, response: PostprocessHook) -> str:
    response.del_cookie(
        name=f"{context.app_key}.refresh",
        path=f"{app_base_route_name(context.app)}/",
        domain=context.auth_info.get("domain")
    )
    return "Logged out."
