import pytest

import hopeit.toolkit.auth as auth
from hopeit.app.context import EventContext, PostprocessHook

from hopeit.server.events import get_event_settings
from hopeit.app.errors import Unauthorized
from hopeit.server.config import AuthType

from hopeit.basic_auth import AuthSettings, login  # type: ignore
from hopeit.basic_auth import ContextUserInfo, AuthInfoExtended, AuthInfo  # type: ignore

from . import mock_app_config, plugin_config  # noqa: F401


async def invoke_login(context: EventContext):
    auth_info = await login.login(None, context)
    cfg = context.settings(key="auth", datatype=AuthSettings)
    assert auth_info.token_type == "BEARER"
    access_token_info = auth.decode_token(auth_info.access_token)
    assert access_token_info["app"] == "test_app.test"
    assert access_token_info["id"] == "id"
    assert access_token_info["email"] == "test@email"
    assert access_token_info["user"] == "test"
    iat = access_token_info["iat"]
    assert access_token_info["exp"] == iat + cfg.access_token_expiration
    assert access_token_info["renew"] > 0
    assert access_token_info["renew"] < 1000.0 * (
        cfg.access_token_expiration - cfg.access_token_renew_window
    )

    refresh_token_info = auth.decode_token(auth_info.refresh_token)
    assert refresh_token_info["app"] == "test_app.test"
    assert refresh_token_info["id"] == "id"
    assert refresh_token_info["email"] == "test@email"
    assert refresh_token_info["user"] == "test"
    iat = refresh_token_info["iat"]
    assert refresh_token_info["exp"] == iat + cfg.refresh_token_expiration

    assert auth_info.user_info == ContextUserInfo(id="id", user="test", email="test@email")
    assert auth_info.access_token_expiration == cfg.access_token_expiration
    assert auth_info.refresh_token_expiration == cfg.refresh_token_expiration
    assert auth_info.renew == access_token_info["renew"]
    return auth_info


async def invoke_postprocess(payload: AuthInfoExtended, context: EventContext):
    hook = PostprocessHook()
    result = await login.__postprocess__(payload, context, response=hook)
    assert hook.cookies["test_app.test.refresh"] == (
        f"Refresh {payload.refresh_token}",
        tuple(),
        {
            "domain": None,
            "expires": 3600,
            "httponly": "true",
            "max_age": 3600,
            "path": "/api/test-app/test/",
        },
    )
    assert result == AuthInfo(
        access_token=payload.access_token, token_type=payload.token_type, renew=payload.renew
    )


async def execute_flow(context):
    auth_info = await invoke_login(context)
    await invoke_postprocess(auth_info, context)


def _event_context(mock_app_config, plugin_config):  # noqa: F811
    return EventContext(
        app_config=mock_app_config,
        plugin_config=plugin_config,
        event_name="login",
        settings=get_event_settings(plugin_config.effective_settings, "login"),
        track_ids={},
        auth_info={"allowed": True, "auth_type": AuthType.BASIC, "payload": "dGVzdDpwYXNz"},
    )


async def test_login(mock_app_config, plugin_config):  # noqa: F811
    auth.init(mock_app_config.app_key(), mock_app_config.server.auth)
    context = _event_context(mock_app_config, plugin_config)
    await execute_flow(context)


async def test_login_unauthorized(mock_app_config, plugin_config):  # noqa: F811
    auth.init(mock_app_config.app_key(), mock_app_config.server.auth)
    context = _event_context(mock_app_config, plugin_config)
    context.auth_info["auth_type"] = "UNKNOWN"
    with pytest.raises(Unauthorized):
        await execute_flow(context)
