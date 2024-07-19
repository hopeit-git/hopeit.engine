import pytest  # type: ignore
from datetime import datetime, timedelta, timezone

import hopeit.toolkit.auth as auth
from hopeit.app.context import EventContext, PostprocessHook
from hopeit.server.events import get_event_settings
from hopeit.app.errors import Unauthorized
from hopeit.server.config import AuthType

from hopeit.basic_auth import logout, AuthSettings  # type: ignore

from . import mock_app_config, plugin_config  # noqa: F401


async def invoke_logout(context: EventContext):
    auth_info = await logout.logout(None, context)
    assert auth_info is None


async def invoke_postprocess(payload: None, context: EventContext):
    hook = PostprocessHook()
    result = await logout.__postprocess__(payload, context, response=hook)
    assert hook.del_cookies == [
        ("test_app.test.refresh", (), {"path": "/api/test-app/test/", "domain": None})
    ]
    assert result == "Logged out."


async def execute_flow(context):
    await invoke_logout(context)
    await invoke_postprocess(None, context)


def _event_context(mock_app_config, plugin_config):  # noqa: F811
    settings = get_event_settings(plugin_config.effective_settings, "logout")
    cfg = settings(key="auth", datatype=AuthSettings)
    iat = datetime.now(tz=timezone.utc)
    timeout = cfg.access_token_expiration
    return EventContext(
        app_config=mock_app_config,
        plugin_config=plugin_config,
        event_name="logout",
        settings=settings,
        track_ids={},
        auth_info={
            "allowed": True,
            "auth_type": AuthType.REFRESH,
            "payload": {
                "id": "id",
                "user": "test",
                "email": "test@email",
                "iat": iat,
                "exp": iat + timedelta(seconds=timeout),
            },
        },
    )


@pytest.mark.asyncio
async def test_logout(mock_app_config, plugin_config):  # noqa: F811
    auth.init(mock_app_config.app_key(), mock_app_config.server.auth)
    context = _event_context(mock_app_config, plugin_config)
    await execute_flow(context)


@pytest.mark.asyncio
async def test_logout_unauthorized(mock_app_config, plugin_config):  # noqa: F811
    auth.init(mock_app_config.app_key(), mock_app_config.server.auth)
    context = _event_context(mock_app_config, plugin_config)
    context.auth_info["auth_type"] = "UNKNOWN"
    with pytest.raises(Unauthorized):
        await execute_flow(context)
