from hopeit.dataobjects import dataclass
import pytest

from hopeit.app.config import Compression, EventLoggingConfig, EventStreamConfig, Serialization
from hopeit.app.context import EventContext, PostprocessHook
from hopeit.dataobjects import dataobject
from hopeit.server.config import AuthType
from hopeit.server.events import EventHandler, get_event_settings
from mock_engine import MockStreamManager

from mock_app import MockData, MockResult, mock_app_config  # type: ignore  # noqa: F401
from mock_plugin import mock_plugin_config  # type: ignore  # noqa: F401


async def mock_handle_request_response_event(app_config, *, payload, expected):
    settings = get_event_settings(app_config.effective_settings, 'mock_post_event')
    handler = EventHandler(
        app_config=app_config,
        plugins=[],
        effective_events=app_config.events,
        settings=app_config.effective_settings
    )
    context = EventContext(
        app_config=app_config,
        plugin_config=app_config,
        event_name='mock_post_event',
        settings=settings,
        track_ids=MockStreamManager.test_track_ids,
        auth_info={'auth_type': AuthType.UNSECURED, 'allowed': 'true'}
    )
    async for response in handler.handle_async_event(context=context, query_args={"query_arg1": payload.value},
                                                     payload=payload):
        assert response == expected


async def mock_handle_postprocess(app_config, *, payload, expected, expected_response):
    settings = get_event_settings(app_config.effective_settings, 'plugin_event')
    handler = EventHandler(
        app_config=app_config,
        plugins=[],
        effective_events=app_config.events,
        settings=app_config.effective_settings
    )
    context = EventContext(
        app_config=app_config,
        plugin_config=app_config,
        event_name='plugin_event',
        settings=settings,
        track_ids={},
        auth_info={'auth_type': AuthType.UNSECURED, 'allowed': 'true'}
    )
    intermediate_result = None
    async for res in handler.handle_async_event(context=context, query_args={}, payload=None):
        intermediate_result = res
    hook = PostprocessHook()
    response = await handler.postprocess(context=context, payload=intermediate_result, response=hook)
    assert hook.headers == expected_response['headers']
    assert hook.cookies == expected_response['cookies']
    assert hook.status == expected_response['status']
    assert response == expected


async def mock_handle_spawn_event(app_config, *, payload, expected, stream_name):
    settings = get_event_settings(app_config.effective_settings, 'mock_spawn_event')
    handler = EventHandler(
        app_config=app_config,
        plugins=[],
        effective_events=app_config.events,
        settings=app_config.effective_settings
    )
    context = EventContext(
        app_config=app_config,
        plugin_config=app_config,
        event_name='mock_spawn_event',
        settings=settings,
        track_ids=MockStreamManager.test_track_ids,
        auth_info={'auth_type': AuthType.UNSECURED, 'allowed': 'true'}
    )
    event_count = 0
    async for result in handler.handle_async_event(context=context, query_args={}, payload=payload.value):
        assert result.value.startswith(expected.value)
        event_count += 1
    assert event_count == 3


@pytest.mark.asyncio
async def test_handle_async_event_ok_case(mock_app_config):  # noqa: F811
    await mock_handle_request_response_event(
        mock_app_config, payload=MockData("ok"), expected=MockResult("ok: ok")
    )


@pytest.mark.asyncio
async def test_handle_async_event_special_case(mock_app_config):  # noqa: F811
    await mock_handle_request_response_event(
        mock_app_config, payload=MockData("no-ok"), expected=MockResult("None")
    )


@pytest.mark.asyncio
async def test_handle_spawn_event(monkeypatch, mock_app_config):  # noqa: F811
    expected_prefix = MockData("stream: ok.")
    monkeypatch.setattr(MockStreamManager, 'test_payload', expected_prefix)
    await mock_handle_spawn_event(
        mock_app_config, payload=MockData("ok"),
        expected=expected_prefix, stream_name='mock_write_stream_event'
    )


@pytest.mark.asyncio
async def test_postprocess(mock_plugin_config):  # noqa: F811
    await mock_handle_postprocess(
        mock_plugin_config,
        payload=MockData("ok"),
        expected="PluginEvent.postprocess",
        expected_response={
            'cookies': {'PluginCookie': ('PluginCookieValue', tuple(), {})},
            'headers': {'PluginHeader': 'PluginHeaderValue'},
            'status': 999
        }
    )


@dataobject
@dataclass
class CustomSetting:
    custom: str


@dataobject
@dataclass
class CustomEventSettings:
    custom_setting: CustomSetting


def test_get_event_settings(mock_app_config):  # noqa: F811
    event_name = "mock_stream_event"
    settings = get_event_settings(mock_app_config.effective_settings, event_name)
    assert settings.response_timeout == 60.0
    assert settings.logging == EventLoggingConfig(extra_fields=['value'], stream_fields=['stream.msg_id'])
    assert settings.stream == EventStreamConfig(
        timeout=60.0, target_max_len=0, throttle_ms=0, step_delay=0, batch_size=100,
        compression=Compression.LZ4, serialization=Serialization.JSON_BASE64
    )
    assert settings(datatype=CustomEventSettings) == CustomEventSettings(
        custom_setting=CustomSetting(custom="value")
    )
    assert settings(key="custom_extra_settings", datatype=CustomEventSettings) == CustomEventSettings(
        custom_setting=CustomSetting(custom="value")
    )


def test_get_event_settings_split_event(mock_app_config):  # noqa: F811
    event_name = "mock_shuffle_event"
    settings = get_event_settings(mock_app_config.effective_settings, event_name)
    assert settings == get_event_settings(
        mock_app_config.effective_settings, "mock_shuffle_event$consume_stream"
    )
