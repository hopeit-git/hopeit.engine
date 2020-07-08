import pytest  # type: ignore
from datetime import datetime, timedelta

import hopeit.toolkit.auth as auth
from hopeit.app.context import EventContext, PostprocessHook

from hopeit.basic_auth import logout  # type: ignore
from hopeit.app.errors import Unauthorized
from hopeit.server.config import AuthType
from . import mock_app_config, plugin_config  # noqa: F401


async def invoke_logout(context: EventContext):
    auth_info = await logout.logout(None, context)
    assert auth_info is None


async def invoke_postprocess(payload: None, context: EventContext):
    hook = PostprocessHook()
    result = await logout.__postprocess__(payload, context, response=hook)
    assert hook.del_cookies == [('test_app.test.refresh', (), {'path': '/api/test-app/test/', 'domain': None})]
    assert result == 'Logged out.'


async def execute_flow(context):
    await invoke_logout(context)
    await invoke_postprocess(None, context)


def _event_context(mock_app_config, plugin_config):  # noqa: F811
    iat = datetime.now()
    timeout = plugin_config.env['auth']['access_token_expiration']
    return EventContext(
        app_config=mock_app_config,
        plugin_config=plugin_config,
        event_name='login',
        track_ids={},
        auth_info={
            'allowed': True,
            'auth_type': AuthType.REFRESH,
            'payload': {'id': 'id', 'user': 'test', 'email': 'test@email', 'iat': iat,
                        'exp': iat + timedelta(seconds=timeout)}
        }
    )


@pytest.mark.asyncio
async def test_logout(mock_app_config, plugin_config):  # noqa: F811
    auth.init(mock_app_config.server.auth)
    context = _event_context(mock_app_config, plugin_config)
    await execute_flow(context)


@pytest.mark.asyncio
async def test_logout_unauthorized(mock_app_config, plugin_config):  # noqa: F811
    auth.init(mock_app_config.server.auth)
    context = _event_context(mock_app_config, plugin_config)
    context.auth_info['auth_type'] = "UNKNOWN"
    with pytest.raises(Unauthorized):
        await execute_flow(context)
