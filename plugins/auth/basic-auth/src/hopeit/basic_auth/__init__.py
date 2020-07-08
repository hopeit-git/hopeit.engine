"""
basic-auth plugin app, helper classes and methods
"""
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import random

import hopeit.toolkit.auth as auth
from hopeit.app.api import app_base_route_name
from hopeit.app.config import AppDescriptor
from hopeit.app.context import EventContext, PostprocessHook
from hopeit.dataobjects import dataobject
from hopeit.server.config import AuthType

__all__ = [
    'ContextUserInfo',
    'AuthInfoExtended',
    'AuthInfo',
    'authorize',
    'set_refresh_token'
]


@dataobject
@dataclass
class ContextUserInfo:
    """
    User info that will be available in context during events execution
    """
    id: str
    user: str
    email: str


@dataobject
@dataclass
class AuthInfoExtended:
    """
    Internal class containing auth info to be passed from events
    to postprocess hooks.
    To share data with external apps or engine use to_auth_info()
    """
    access_token: str
    refresh_token: str
    token_type: str
    access_token_expiration: int
    refresh_token_expiration: int
    renew: int
    app: str
    user_info: ContextUserInfo

    def to_auth_info(self):
        return AuthInfo(
            access_token=self.access_token,
            token_type=self.token_type,
            renew=self.renew
        )


@dataobject
@dataclass
class AuthInfo:
    """
    Minimal auth info that should be returned outside this app
    """
    access_token: str
    token_type: str
    renew: int


def authorize(context: EventContext,
              user_info: ContextUserInfo,
              now: datetime) -> AuthInfoExtended:
    """
    Authorize user and returns auth info containing tokens for api access and authorization renewal

    :param context: event context from app requesting authorization or login happened
    :param user_info: already validated user info to be encoded in tokens:
        Notice this method wont check if user is valid, invoking app should ensure this.
    :param now: current datetime, fixed as start of authorization process
    :return: AuthInfoExtended, containing new access and refresh tokens
    """
    ate = int(context.env['auth']['access_token_expiration'])
    rte = int(context.env['auth']['refresh_token_expiration'])
    atr = int(context.env['auth']['access_token_renew_window'])
    renew_in = int(1000.0 * max(
        1.0 * ate - 1.0 * atr * (1.0 + 0.5 * random.random()),
        0.5 * ate * (0.5 * random.random() + 0.5)))
    token = _new_access_token(asdict(user_info), context, now, ate, renew_in)
    refresh_token = _new_refresh_token(asdict(user_info), context, now, rte)
    result = AuthInfoExtended(
        app=context.app_key,
        access_token=token,
        refresh_token=refresh_token,
        token_type=AuthType.BEARER.name,
        access_token_expiration=ate,
        refresh_token_expiration=rte,
        renew=renew_in,
        user_info=user_info
    )
    return result


def set_refresh_token(app: AppDescriptor, auth_info: dict, payload: AuthInfoExtended, response: PostprocessHook):
    """
    sets information to a hook providing a way for http servers
    to set an http-only cookie containing the refresh_token
    """
    response.set_cookie(
        name=f"{app.app_key()}.refresh",
        value=f"Refresh {payload.refresh_token}",
        httponly="true",
        expires=payload.refresh_token_expiration,
        max_age=payload.refresh_token_expiration,
        path=f"{app_base_route_name(app)}/",
        domain=auth_info.get("domain")
    )


def _new_access_token(info: dict, context: EventContext, now: datetime, timeout: int, renew: int):
    """
    Returns a new access token encoding `info` and expiring in `access_token_expiration` seconds
    """
    auth_payload = {
        **info,
        "app": context.app_key,
        "iat": now,
        "exp": now + timedelta(seconds=timeout),
        "renew": renew
    }
    return auth.new_token(auth_payload)


def _new_refresh_token(info: dict,
                       context: EventContext,
                       now: datetime,
                       timeout: int):
    """
    Returns a new refresh token encoding `info` and expiring in `refresh_token_expiration` seconds
    """
    auth_payload = {
        **info,
        "app": context.app_key,
        "iat": now,
        "exp": now + timedelta(seconds=timeout)
    }
    return auth.new_token(auth_payload)
