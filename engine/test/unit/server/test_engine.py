import pytest  # type: ignore
from typing import Dict, Optional

from hopeit.app.context import EventContext, PostprocessHook
from hopeit.server.config import AuthType
from hopeit.server.events import EventHandler
from hopeit.streams import StreamOSError
from hopeit.streams.redis import RedisStreamManager

from hopeit.dataobjects import DataObject
from hopeit.app.config import AppConfig
from hopeit.server.engine import AppEngine
from mock_engine import MockEventHandler, MockStreamManager
from mock_app import MockData, MockResult  # type: ignore
from mock_app import mock_app_config  # type: ignore  # noqa: F401
from mock_plugin import mock_plugin_config  # type: ignore  # noqa: F401


async def create_engine(app_config: AppConfig, plugin: AppConfig) -> AppEngine:
    engine = await AppEngine(app_config=app_config, plugins=[plugin]).start()
    assert engine.stream_manager is not None
    return engine


async def create_plugin_engine(plugin: AppConfig) -> AppEngine:
    engine = await AppEngine(app_config=plugin, plugins=[]).start()
    assert engine.stream_manager is None
    return engine


async def invoke_execute(engine: AppEngine,
                         from_app: AppConfig,
                         event_name: str,
                         query_args: dict,
                         payload: DataObject,
                         expected: DataObject,
                         track_ids: Dict[str, str],
                         postprocess_expected: Optional[dict] = None):
    context = EventContext(
        app_config=from_app,
        plugin_config=engine.app_config,
        event_name=event_name,
        track_ids=track_ids,
        auth_info={'auth_type': AuthType.UNSECURED, 'allowed': 'true'}
    )
    res = await engine.execute(
        context=context,
        query_args=query_args,
        payload=payload
    )
    assert res == expected
    if postprocess_expected:
        hook = PostprocessHook()
        await engine.postprocess(context=context, payload=res, response=hook)
        assert hook.headers == postprocess_expected['headers']
        assert hook.cookies == postprocess_expected['cookies']
        assert hook.status == postprocess_expected['status']


def setup_mocks(monkeypatch):
    monkeypatch.setattr(EventHandler, '__init__', MockEventHandler.__init__)
    monkeypatch.setattr(EventHandler, 'handle_async_event', MockEventHandler.handle_async_event)
    monkeypatch.setattr(EventHandler, 'postprocess', MockEventHandler.postprocess)
    monkeypatch.setattr(RedisStreamManager, '__init__', MockStreamManager.__init__)
    monkeypatch.setattr(RedisStreamManager, 'connect', MockStreamManager.connect)
    monkeypatch.setattr(RedisStreamManager, 'write_stream', MockStreamManager.write_stream)
    monkeypatch.setattr(RedisStreamManager,
                        'ensure_consumer_group', MockStreamManager.ensure_consumer_group)
    monkeypatch.setattr(RedisStreamManager, 'read_stream', MockStreamManager.read_stream)
    monkeypatch.setattr(RedisStreamManager, 'ack_read_stream', MockStreamManager.ack_read_stream)
    monkeypatch.setattr(RedisStreamManager, 'close', MockStreamManager.close)


@pytest.mark.asyncio
async def test_execute(monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    payload = MockData("ok")
    expected = MockResult("ok: ok")
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockStreamManager, 'test_payload', expected)
    monkeypatch.setattr(MockEventHandler, 'test_track_ids', None)

    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    await invoke_execute(engine=engine, from_app=engine.app_config,
                         event_name='mock_post_event',
                         query_args={"query_arg1": "ok"},
                         payload=payload,
                         expected=expected,
                         track_ids={"track.session_id": "test_session_id"})
    await engine.stop()


@pytest.mark.asyncio
async def test_execute_plugin(monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    expected = "PluginEvent"
    expected_response = {
        'cookies': {'PluginCookie': ('PluginCookieValue', tuple(), {})},
        'headers': {'PluginHeader': 'PluginHeaderValue'},
        'status': 999
    }

    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', None)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockStreamManager, 'test_payload', expected)
    monkeypatch.setattr(MockEventHandler, 'test_track_ids', None)

    plugin_engine = await create_plugin_engine(plugin=mock_plugin_config)
    await invoke_execute(engine=plugin_engine, from_app=mock_plugin_config,
                         event_name='plugin_event',
                         query_args={},
                         payload=None,
                         expected=expected,
                         track_ids={"track.session_id": "test_session_id"},
                         postprocess_expected=expected_response)
    await plugin_engine.stop()


@pytest.mark.asyncio
async def test_execute_provided_request_id(
        monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    payload = MockData("ok")
    expected = MockResult("ok: ok")
    track_ids = {
        "track.request_id": "test_request_id",
        "track.request_ts": "2020-02-05T17:07:37.771396+00:00",
        "track.session_id": "test_session_id"
    }
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockStreamManager, 'test_payload', expected)
    monkeypatch.setattr(MockEventHandler, 'expected_track_ids', track_ids)

    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    await invoke_execute(engine=engine, from_app=engine.app_config,
                         event_name='mock_post_event',
                         query_args={"query_arg1": "ok"},
                         payload=payload,
                         expected=expected,
                         track_ids=track_ids)
    await engine.stop()


@pytest.mark.asyncio
async def test_read_stream(monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    payload = MockData("ok")
    expected = MockResult("ok: ok")
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockStreamManager, 'test_payload', payload)
    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    monkeypatch.setattr(engine, 'stream_manager', MockStreamManager(address='test'))
    res = await engine.read_stream(event_name='mock_stream_event', test_mode=True)
    assert res == expected
    await engine.stop()


@pytest.mark.asyncio
async def test_service_loop(monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    payload = "stream: service.0"
    expected = MockData("stream: service.0")
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockStreamManager, 'test_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'test_track_ids', None)
    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    monkeypatch.setattr(engine, 'stream_manager', MockStreamManager(address='test'))
    res = await engine.service_loop(event_name='mock_service_event', test_mode=True)
    assert res == expected
    await engine.stop()


@pytest.mark.asyncio
async def test_service_loop_timeout(monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    payload = MockData("timeout")
    expected = MockData("stream: service.1")
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockStreamManager, 'test_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'test_track_ids', None)
    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    monkeypatch.setattr(engine, 'stream_manager', MockStreamManager(address='test'))
    res = await engine.service_loop(event_name='mock_service_timeout', test_mode=True)
    assert isinstance(res, TimeoutError)
    await engine.stop()


@pytest.mark.asyncio
async def test_read_stream_timeout_ok(monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    payload = MockData("ok")
    expected = MockResult("ok: ok")
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockStreamManager, 'test_payload', payload)
    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    monkeypatch.setattr(engine, 'stream_manager', MockStreamManager(address='test'))
    res = await engine.read_stream(event_name='mock_stream_timeout', test_mode=True)
    assert res == expected
    await engine.stop()


@pytest.mark.asyncio
async def test_read_stream_timeout_fail(monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    payload = MockData("timeout")
    expected = MockResult("none")
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockStreamManager, 'test_payload', payload)
    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    monkeypatch.setattr(engine, 'stream_manager', MockStreamManager(address='test'))
    res = await engine.read_stream(event_name='mock_stream_timeout', test_mode=True)
    assert isinstance(res, TimeoutError)
    await engine.stop()


@pytest.mark.asyncio
async def test_read_stream_stop_and_recover(monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    payload = MockData("ok")
    expected = MockResult("ok: ok")
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockStreamManager, 'test_payload', payload)
    monkeypatch.setattr(MockStreamManager, 'error_pattern', [None, TypeError(), None, StreamOSError(), None])
    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    monkeypatch.setattr(engine, 'stream_manager', MockStreamManager(address='test'))
    res = await engine.read_stream(event_name='mock_stream_event', test_mode=True)
    assert res == expected
    await engine.stop()


@pytest.mark.asyncio
async def test_read_stream_failed(monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    payload = MockData("fail")
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', None)
    monkeypatch.setattr(MockStreamManager, 'test_payload', payload)
    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    monkeypatch.setattr(engine, 'stream_manager', MockStreamManager(address='test'))
    res = await engine.read_stream(event_name='mock_stream_event', test_mode=True)
    assert isinstance(res, ValueError)
    await engine.stop()


@pytest.mark.asyncio
async def test_write_stream(monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    payload = MockData("ok")
    expected = MockResult("ok: ok")
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockStreamManager, 'test_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'test_track_ids', None)
    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    stream_manager = MockStreamManager(address='test')
    monkeypatch.setattr(engine, 'stream_manager', stream_manager)
    event_info = mock_app_config.events['mock_write_stream_event']
    await invoke_execute(engine=engine, from_app=engine.app_config,
                         event_name='mock_write_stream_event',
                         query_args={},
                         payload=payload,
                         expected=expected,
                         track_ids={"track.session_id": "test_session_id"})
    assert stream_manager.write_stream_name == event_info.write_stream.name
    assert stream_manager.write_stream_payload == expected
    assert stream_manager.write_target_max_len == 10
    await engine.stop()


@pytest.mark.asyncio
async def test_write_stream_batch(monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    payload = "ok"
    expected = MockData("stream: ok.3")
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockStreamManager, 'test_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'test_track_ids', None)
    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    stream_manager = MockStreamManager(address='test')
    monkeypatch.setattr(engine, 'stream_manager', stream_manager)
    event_info = mock_app_config.events['mock_write_stream_event']
    await invoke_execute(engine=engine, from_app=engine.app_config,
                         event_name='mock_spawn_event',
                         query_args={},
                         payload=payload,
                         expected=expected,
                         track_ids={"track.session_id": "test_session_id"})
    assert stream_manager.write_stream_name == event_info.write_stream.name
    assert stream_manager.write_stream_payload == expected
    assert stream_manager.write_target_max_len == 10
    await engine.stop()


@pytest.mark.asyncio
async def test_execute_collector(monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    payload = MockData(value="ok")
    expected = MockResult(value="step3: ok")
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockStreamManager, 'test_payload', expected)
    monkeypatch.setattr(MockEventHandler, 'test_track_ids', None)

    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    await invoke_execute(engine=engine, from_app=engine.app_config,
                         event_name='mock_collector',
                         query_args={},
                         payload=payload,
                         expected=expected,
                         track_ids={"track.session_id": "test_session_id"})
    await engine.stop()
